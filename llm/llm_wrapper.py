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
from typing import List, Dict, Any, Optional, Generator, Union, Tuple

from .llm_client import LLMClient, LLMResponse

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
        model: str = "gpt-4-turbo-preview",
        focus_mode: bool = False,
        function_schemas: Optional[List[Dict]] = None
    ):
        """
        Initialize the LLM wrapper.
        
        Args:
            system_prompt: The system prompt to always include
            llm_client: An existing LLMClient instance, or None to create a new one
            max_history_tokens: Maximum number of tokens to include from history
            model: The LLM model to use
            focus_mode: Whether to enable focus mode by default
            function_schemas: Optional function schemas for tool use
        """
        self.system_prompt = system_prompt
        self.client = llm_client or LLMClient()
        self.max_history_tokens = max_history_tokens
        self.model = model
        self.history: List[Dict[str, str]] = []
        self.focus_mode = focus_mode
        self.function_schemas = function_schemas
        
        # Rough token estimation (this is approximate)
        self._tokens_per_message = 4  # Every message follows <im_start>{role/name}\n{content}<im_end>\n
        self._tokens_per_char = 0.25  # Rough estimate for tokens per character
        
        logger.info(f"LLMWrapper initialized with system prompt: {system_prompt[:50]}...")
        logger.info(f"Focus mode: {focus_mode}")
        logger.info(f"Function schemas provided: {bool(function_schemas)}")
        
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
        function_schemas: Optional[List[Dict]] = None
    ) -> Union[LLMResponse, Generator[str, None, LLMResponse]]:
        """
        Send a message to the LLM and get a response.
        
        Args:
            user_input: The user's input message
            focus_mode: Whether to use focus mode (overrides the instance setting if provided)
            stream: Whether to stream the response
            function_schemas: Optional function schemas for tool use (overrides the instance setting if provided)
            
        Returns:
            LLM response or generator
        """
        # Use provided focus_mode if given, otherwise use instance setting
        use_focus_mode = self.focus_mode if focus_mode is None else focus_mode
        
        # Use provided function_schemas if given, otherwise use instance setting
        use_function_schemas = function_schemas if function_schemas is not None else self.function_schemas
        
        messages = self._prepare_messages(user_input, use_focus_mode)
        
        # Call the LLM
        response = self.client.call_llm(
            messages=messages,
            stream=stream,
            function_schemas=use_function_schemas,
            model=self.model
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