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
from litellm.utils import ModelResponse

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
        
        # Calculate tokens used by system prompt and current user input
        system_tokens = self._estimate_tokens(self.system_prompt)
        
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
            
        user_tokens = self._estimate_tokens(user_content)
        
        # Calculate remaining token budget for history
        remaining_tokens = self.max_history_tokens - system_tokens - user_tokens
        
        # Add as much history as possible, prioritizing recent messages
        history_messages = []
        token_count = 0
        
        for message in reversed(self.history):
            msg_tokens = self._estimate_tokens(message["content"])
            if token_count + msg_tokens <= remaining_tokens:
                history_messages.insert(0, message)
                token_count += msg_tokens
            else:
                break
                
        messages.extend(history_messages)
        
        # Add current user message
        messages.append({"role": "user", "content": user_content})
        
        logger.info(f"Prepared {len(messages)} messages with approximately {system_tokens + token_count + user_tokens} tokens")
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
        
        # Call the LLM
        response = self.client.call_llm(
            messages=messages,
            stream=stream,
            function_schemas=function_schemas,
            model=use_model
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