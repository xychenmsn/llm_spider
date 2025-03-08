#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - LLM Wrapper

This module provides a wrapper around the LLMClient that adds:
1. Persistent system prompt
2. Chat history management
3. Focus mode to ensure user queries align with the system prompt
"""

import json
import logging
import os
from typing import List, Dict, Any, Optional, Generator, Union, Tuple

from dotenv import load_dotenv
import litellm
from litellm.utils import ModelResponse, token_counter, get_max_tokens

from .llm_client import LLMClient, LLMResponse, LLMProvider
from .function_manager import get_function_schemas

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

class LLMWrapper:
    """
    A wrapper around LLMClient that adds system prompt management,
    chat history tracking, and focus mode functionality.
    """
    
    def __init__(
        self, 
        system_prompt: str,
        llm_client: Optional[LLMClient] = None,
        max_history_tokens: int = 4000,
        model: str = None,
        provider: Union[str, LLMProvider] = None,
        focus_mode: bool = False,
        enable_functions: bool = False,
        custom_function_schemas: Optional[List[Dict]] = None
    ):
        """
        Initialize the LLM wrapper.
        
        Args:
            system_prompt: The system prompt to always include
            llm_client: An existing LLMClient instance, or None to create a new one
            max_history_tokens: Maximum number of tokens to include from history
            model: The LLM model to use
            provider: The LLM provider to use
            focus_mode: Whether to enable focus mode by default
            enable_functions: Whether to enable function calling
            custom_function_schemas: Optional custom function schemas to use instead of registered ones
        """
        self.system_prompt = system_prompt
        
        # Initialize the LLM client
        if llm_client:
            self.client = llm_client
        else:
            self.client = LLMClient(
                provider=provider,
                model=model
            )
            
        self.model = model or self.client.model
        self.max_history_tokens = max_history_tokens
        self.history: List[Dict[str, str]] = []
        self.focus_mode = focus_mode
        self.enable_functions = enable_functions
        self.custom_function_schemas = custom_function_schemas
        
        # Rough token estimation (this is approximate)
        self._tokens_per_message = 4  # Every message follows <im_start>{role/name}\n{content}<im_end>\n
        self._tokens_per_char = 0.25  # Rough estimate for tokens per character
        
        logger.info(f"LLMWrapper initialized with system prompt: {system_prompt[:50]}...")
        logger.info(f"Focus mode: {focus_mode}")
        logger.info(f"Function calling enabled: {enable_functions}")
        logger.info(f"Custom function schemas provided: {bool(custom_function_schemas)}")
        logger.info(f"Using model: {self.model}")
        logger.info(f"Using provider: {self.client.provider}")
        
    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate the number of tokens in a text string.
        This is a rough approximation.
        
        Args:
            text: The text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        return int(len(text) * self._tokens_per_char) + self._tokens_per_message
    
    def _count_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        Count tokens in a list of messages using litellm's token counter.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Token count
        """
        try:
            # Use litellm's token counter for accurate counting
            count = token_counter(model=self.model, messages=messages)
            logger.debug(f"Token count for messages: {count}")
            return count
        except Exception as e:
            logger.warning(f"Error counting tokens with litellm: {str(e)}. Falling back to estimation.")
            # Fall back to estimation if litellm counter fails
            return sum(self._estimate_tokens(msg.get("content", "")) for msg in messages)
    
    def _get_max_tokens(self, model: str = None) -> int:
        """
        Get the maximum context length for a model.
        
        Args:
            model: Model name (optional, uses self.model if not provided)
            
        Returns:
            Maximum context length in tokens
        """
        model_to_check = model or self.model
        try:
            # Use litellm's get_max_tokens function
            max_tokens = get_max_tokens(model_to_check)
            logger.debug(f"Max tokens for {model_to_check}: {max_tokens}")
            return max_tokens
        except Exception as e:
            logger.warning(f"Error getting max tokens for {model_to_check}: {str(e)}. Using default value.")
            # Default values for common models if litellm fails
            default_limits = {
                "gpt-3.5-turbo": 4096,
                "gpt-4": 8192,
                "gpt-4-turbo": 128000,
                "claude-3-opus-20240229": 200000,
                "claude-3-sonnet-20240229": 180000
            }
            # Return default or conservative fallback
            return default_limits.get(model_to_check, 4000)

    def _prepare_messages(self, user_input: str, focus_mode: bool = False) -> List[Dict[str, str]]:
        """
        Prepare messages for the LLM call, including system prompt and history.
        
        Args:
            user_input: The current user input
            focus_mode: Whether to use focus mode
            
        Returns:
            List of message dictionaries ready for the LLM
        """
        # Start with system prompt
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # Prepare user input - wrap in JSON if focus mode is enabled
        if focus_mode:
            focus_wrapper = {
                "user_input": user_input,
                "instructions": "If this input aligns with your system instructions, respond normally. "
                               "If it doesn't, politely decline and remind the user of your purpose."
            }
            user_content = json.dumps(focus_wrapper)
        else:
            user_content = user_input
        
        # Create a copy of the current user message to calculate its tokens
        current_user_message = {"role": "user", "content": user_content}
        
        # Count tokens for system prompt and current user message
        system_and_user_messages = [messages[0], current_user_message]
        system_and_user_tokens = self._count_tokens(system_and_user_messages)
        
        # Calculate remaining token budget for history
        max_model_tokens = self._get_max_tokens()
        remaining_tokens = min(self.max_history_tokens, max_model_tokens - system_and_user_tokens - 500)  # Reserve 500 tokens for response
        
        if remaining_tokens <= 0:
            logger.warning(f"Not enough tokens for history. System and user message already use {system_and_user_tokens} tokens.")
            # Just use system prompt and current user message
            messages.append(current_user_message)
            return messages
        
        # Add as much history as possible, prioritizing recent messages
        history_messages = []
        token_count = 0
        
        # Create temporary messages to check token count
        for message in reversed(self.history):
            temp_messages = system_and_user_messages + history_messages + [message]
            message_tokens = self._count_tokens(temp_messages) - system_and_user_tokens - token_count
            
            if token_count + message_tokens <= remaining_tokens:
                history_messages.insert(0, message)
                token_count += message_tokens
            else:
                break
                
        messages.extend(history_messages)
        
        # Add current user message
        messages.append(current_user_message)
        
        total_tokens = self._count_tokens(messages)
        logger.info(f"Prepared {len(messages)} messages with {total_tokens} tokens")
        
        # Check if we're approaching the model's limit
        if total_tokens > max_model_tokens * 0.9:  # 90% of max context
            logger.warning(f"Input size approaching limit: {total_tokens}/{max_model_tokens}")
        
        return messages
    
    def chat(
        self, 
        user_input: str, 
        focus_mode: Optional[bool] = None,
        stream: bool = True,
        enable_functions: Optional[bool] = None,
        custom_function_schemas: Optional[List[Dict]] = None,
        model: Optional[str] = None
    ) -> Union[LLMResponse, Generator[str, None, LLMResponse]]:
        """
        Send a message to the LLM and get a response.
        
        Args:
            user_input: The user's input message
            focus_mode: Whether to use focus mode (overrides the instance setting if provided)
            stream: Whether to stream the response
            enable_functions: Whether to enable function calling (overrides the instance setting if provided)
            custom_function_schemas: Optional custom function schemas (overrides the instance setting if provided)
            model: Optional model override
            
        Returns:
            LLM response or generator
        """
        # Use provided settings if given, otherwise use instance settings
        use_focus_mode = self.focus_mode if focus_mode is None else focus_mode
        use_enable_functions = self.enable_functions if enable_functions is None else enable_functions
        use_custom_schemas = custom_function_schemas if custom_function_schemas is not None else self.custom_function_schemas
        use_model = model if model is not None else self.model
        
        messages = self._prepare_messages(user_input, use_focus_mode)
        
        # Determine which function schemas to use
        function_schemas = None
        if use_enable_functions:
            if use_custom_schemas:
                function_schemas = use_custom_schemas
            else:
                function_schemas = get_function_schemas()
        
        # Check token count before sending
        total_tokens = self._count_tokens(messages)
        max_model_tokens = self._get_max_tokens(use_model)
        
        # Set up context window fallback if we're close to the limit
        context_window_fallback_dict = None
        if total_tokens > max_model_tokens * 0.9:  # 90% of max context
            logger.warning(f"Using context window fallback due to large input: {total_tokens}/{max_model_tokens}")
            context_window_fallback_dict = {"truncate_mode": "auto"}
        
        # Call the LLM
        response = self.client.call_llm(
            messages=messages,
            stream=stream,
            function_schemas=function_schemas,
            model=use_model,
            context_window_fallback_dict=context_window_fallback_dict
        )
        
        # If streaming, we need to process the generator
        if stream:
            def process_stream():
                content_chunks = []
                final_response = None
                
                for chunk in response:
                    if isinstance(chunk, str):
                        content_chunks.append(chunk)
                        yield chunk
                    elif isinstance(chunk, LLMResponse):
                        final_response = chunk
                        
                # After streaming completes, update history
                if final_response:
                    # Add user message to history
                    self.history.append({"role": "user", "content": user_input})
                    
                    # Add assistant response to history
                    self.history.append({
                        "role": "assistant", 
                        "content": final_response.content
                    })
                    
                    yield final_response
                
            return process_stream()
        else:
            # For non-streaming responses, update history immediately
            self.history.append({"role": "user", "content": user_input})
            self.history.append({
                "role": "assistant", 
                "content": response.content
            })
            
            return response
    
    def clear_history(self) -> None:
        """Clear the chat history."""
        self.history = []
        logger.info("Chat history cleared")
        
    def get_history(self) -> List[Dict[str, str]]:
        """Get the current chat history."""
        return self.history.copy()
        
    def set_system_prompt(self, system_prompt: str) -> None:
        """Set a new system prompt."""
        self.system_prompt = system_prompt
        logger.info(f"System prompt updated: {system_prompt[:50]}...")
        
    def set_model(self, model: str) -> None:
        """Set a new model."""
        self.model = model
        logger.info(f"Model updated to: {model}")
        
    def set_provider(self, provider: Union[str, LLMProvider]) -> None:
        """Set a new provider."""
        # Create a new client with the new provider
        self.client = LLMClient(
            provider=provider,
            model=self.model
        )
        logger.info(f"Provider updated to: {provider}")
        
    def set_focus_mode(self, focus_mode: bool) -> None:
        """Set focus mode."""
        self.focus_mode = focus_mode
        logger.info(f"Focus mode set to: {focus_mode}")
        
    def set_enable_functions(self, enable_functions: bool) -> None:
        """Set function calling."""
        self.enable_functions = enable_functions
        logger.info(f"Function calling set to: {enable_functions}")
        
    def set_custom_function_schemas(self, custom_function_schemas: Optional[List[Dict]]) -> None:
        """Set custom function schemas."""
        self.custom_function_schemas = custom_function_schemas
        logger.info(f"Custom function schemas updated: {bool(custom_function_schemas)}") 