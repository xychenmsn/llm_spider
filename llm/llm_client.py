#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - LLM Client

This module provides a reusable client class for LLM interactions.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Generator, Union
from dataclasses import dataclass

from dotenv import load_dotenv
import openai
from openai.types.chat import ChatCompletionMessage
from openai.types.chat.chat_completion_message import ChatCompletionMessageToolCall
from openai.types.chat.chat_completion_message_tool_call import Function

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

@dataclass
class LLMResponse:
    """Data class to hold LLM response information"""
    content: str
    tool_calls: Optional[List[ChatCompletionMessageToolCall]] = None
    role: str = "assistant"

class LLMClient:
    """A reusable client for LLM interactions."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the LLM client.
        
        Args:
            api_key: OpenAI API key. If None, will try to get from environment.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize the OpenAI client."""
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            logger.warning("OpenAI API key not found or not set.")
            return

        try:
            self.client = openai.OpenAI(api_key=self.api_key)
            logger.info("OpenAI API connection successful")
        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {str(e)}")
            self.client = None

    def _reconstruct_message_from_chunks(self, chunks) -> ChatCompletionMessage:
        """Reconstruct a complete message from streaming chunks."""
        content = ""
        role = "assistant"
        tool_calls_dict = {}

        for chunk in chunks:
            delta = chunk.choices[0].delta
            
            if hasattr(delta, 'content') and delta.content:
                content += delta.content
            
            if hasattr(delta, 'tool_calls') and delta.tool_calls:
                for tool_call in delta.tool_calls:
                    if hasattr(tool_call, 'index'):
                        idx = tool_call.index
                        
                        if idx not in tool_calls_dict:
                            tool_calls_dict[idx] = {
                                "id": getattr(tool_call, 'id', None),
                                "type": "function",
                                "function": {
                                    "name": "",
                                    "arguments": ""
                                }
                            }
                        
                        if hasattr(tool_call, 'id') and tool_call.id:
                            tool_calls_dict[idx]["id"] = tool_call.id
                        
                        if hasattr(tool_call, 'function'):
                            if hasattr(tool_call.function, 'name') and tool_call.function.name:
                                tool_calls_dict[idx]["function"]["name"] = tool_call.function.name
                            
                            if hasattr(tool_call.function, 'arguments') and tool_call.function.arguments:
                                tool_calls_dict[idx]["function"]["arguments"] += tool_call.function.arguments

        tool_calls = []
        for idx, tc_data in tool_calls_dict.items():
            function = Function(name=tc_data["function"]["name"], arguments=tc_data["function"]["arguments"])
            tool_call = ChatCompletionMessageToolCall(
                id=tc_data["id"] or f"call_{idx}",
                type=tc_data["type"],
                function=function
            )
            tool_calls.append(tool_call)

        return ChatCompletionMessage(role=role, content=content, tool_calls=tool_calls if tool_calls else None)

    def call_llm(
        self,
        messages: List[Dict[str, str]],
        stream: bool = True,
        function_schemas: Optional[List[Dict]] = None,
        model: str = "gpt-4-turbo-preview",
        callback_stream: Optional[callable] = None,
        callback_tool_call: Optional[callable] = None
    ) -> Union[LLMResponse, Generator[str, None, None]]:
        """Call the LLM with the given messages.
        
        Args:
            messages: List of message dictionaries
            stream: Whether to stream the response
            function_schemas: Optional list of function schemas
            model: The model to use
            callback_stream: Optional callback for streaming chunks
            callback_tool_call: Optional callback for tool calls
            
        Returns:
            If stream=False, returns LLMResponse
            If stream=True, returns a generator of response chunks
        
        Raises:
            RuntimeError: If OpenAI client is not initialized
            Exception: For any OpenAI API errors
        """
        if self.client is None:
            raise RuntimeError("OpenAI client is not properly initialized. Please check your API key.")

        logger.info(f"Calling LLM with model: {model}")
        logger.info(f"Stream mode: {stream}")
        logger.info(f"Number of messages: {len(messages)}")
        logger.info(f"Function schemas provided: {bool(function_schemas)}")

        params = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1000,
            "stream": stream
        }

        if function_schemas:
            params["tools"] = function_schemas

        try:
            response = self.client.chat.completions.create(**params)

            if stream:
                collected_chunks = []
                collected_messages = []
                complete_response_message = None

                def process_stream():
                    nonlocal complete_response_message
                    
                    for chunk in response:
                        if hasattr(chunk.choices[0].delta, 'tool_calls') and chunk.choices[0].delta.tool_calls:
                            collected_chunks.append(chunk)
                            continue

                        content = chunk.choices[0].delta.content
                        if content:
                            collected_messages.append(content)
                            if callback_stream:
                                callback_stream(content)
                            yield content

                    if collected_chunks:
                        complete_response_message = self._reconstruct_message_from_chunks(collected_chunks)
                        
                        if callback_tool_call and complete_response_message.tool_calls:
                            for tool_call in complete_response_message.tool_calls:
                                function_name = tool_call.function.name
                                function_args = json.loads(tool_call.function.arguments)
                                callback_tool_call(function_name, function_args)

                return process_stream()
            else:
                response_message = response.choices[0].message
                
                if callback_tool_call and response_message.tool_calls:
                    for tool_call in response_message.tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        callback_tool_call(function_name, function_args)

                return LLMResponse(
                    content=response_message.content,
                    tool_calls=response_message.tool_calls,
                    role=response_message.role
                )

        except Exception as e:
            logger.error(f"Error in LLM call: {str(e)}")
            raise 