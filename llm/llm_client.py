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
    tool_calls: Optional[List[Dict[str, Any]]] = None
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
    ) -> Union[LLMResponse, Generator[str, None, LLMResponse]]:
        """Call the LLM with the given messages."""
        if self.client is None:
            raise RuntimeError("OpenAI client is not properly initialized. Please check your API key.")

        logger.info(f"Calling LLM with model: {model}")
        logger.info(f"Stream mode: {stream}")
        logger.info(f"Number of messages: {len(messages)}")
        logger.info(f"Function schemas provided: {bool(function_schemas)}")
        
        # Log messages (excluding potentially sensitive system prompts)
        for msg in messages:
            if msg['role'] != 'system':
                logger.info(f"Message ({msg['role']}): {msg['content'][:100]}...")

        params = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1000,
            "stream": stream
        }

        if function_schemas:
            params["tools"] = function_schemas
            logger.info(f"Function schemas: {json.dumps(function_schemas, indent=2)}")

        try:
            logger.info("Making OpenAI API call...")
            response = self.client.chat.completions.create(**params)
            logger.info("OpenAI API call successful")

            if stream:
                collected_chunks = []
                collected_messages = []

                def process_stream():
                    nonlocal collected_chunks, collected_messages
                    
                    try:
                        for chunk in response:
                            delta = chunk.choices[0].delta
                            logger.debug(f"Received chunk: {delta}")
                            
                            # Handle tool calls if present
                            if hasattr(delta, 'tool_calls') and delta.tool_calls:
                                logger.info(f"Received tool call chunk: {delta.tool_calls}")
                                collected_chunks.append(chunk)
                            
                            # Handle content if present
                            if hasattr(delta, 'content') and delta.content:
                                logger.debug(f"Received content chunk: {delta.content}")
                                collected_messages.append(delta.content)
                                yield delta.content

                        logger.info(f"Stream complete. Collected {len(collected_chunks)} tool call chunks and {len(collected_messages)} content chunks")

                        # After stream ends, yield the complete response with tool calls
                        # We don't need to include the content again since it was already streamed
                        if collected_chunks:
                            logger.info("Processing collected tool call chunks...")
                            complete_message = self._reconstruct_message_from_chunks(collected_chunks)
                            logger.info(f"Reconstructed message: {complete_message}")
                            
                            # Use the already collected content instead of potentially duplicating it
                            content = "".join(collected_messages)
                            
                            yield LLMResponse(
                                content=content,
                                tool_calls=[{
                                    "name": tc.function.name,
                                    "arguments": json.loads(tc.function.arguments)
                                } for tc in complete_message.tool_calls] if complete_message.tool_calls else None,
                                role=complete_message.role
                            )
                        else:
                            logger.info("No tool calls found, yielding content-only response")
                            yield LLMResponse(
                                content="".join(collected_messages),
                                role="assistant"
                            )
                    except Exception as e:
                        logger.error(f"Error in stream processing: {str(e)}", exc_info=True)
                        raise

                return process_stream()
            else:
                response_message = response.choices[0].message
                logger.info(f"Received non-streaming response: {response_message}")
                
                return LLMResponse(
                    content=response_message.content,
                    tool_calls=[{
                        "name": tc.function.name,
                        "arguments": json.loads(tc.function.arguments)
                    } for tc in response_message.tool_calls] if response_message.tool_calls else None,
                    role=response_message.role
                )

        except Exception as e:
            logger.error(f"Error in LLM call: {str(e)}", exc_info=True)
            raise 