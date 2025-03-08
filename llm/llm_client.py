#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - LLM Client

This module provides a reusable client class for LLM interactions with support for
multiple providers including OpenAI, Anthropic, and local LLM servers.
"""

import os
import json
import logging
import datetime
import pathlib
from typing import List, Dict, Any, Optional, Generator, Union, Literal
from dataclasses import dataclass
from enum import Enum, auto

from dotenv import load_dotenv
import litellm
from litellm.utils import ModelResponse

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

class LLMProvider(str, Enum):
    """Enum for supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    LLAMA_CPP = "llama_cpp"
    LLMSTUDIO = "llmstudio"
    CUSTOM = "custom"

@dataclass
class LLMResponse:
    """Data class to hold LLM response information"""
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    role: str = "assistant"

class LLMClient:
    """A reusable client for LLM interactions with multiple providers."""
    
    def __init__(
        self, 
        provider: Union[str, LLMProvider] = None,
        model: str = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None
    ):
        """Initialize the LLM client.
        
        Args:
            provider: LLM provider (openai, anthropic, ollama, etc.)
            model: Model name to use
            api_key: API key for the provider. If None, will try to get from environment.
            api_base: Base URL for API calls. Useful for local deployments.
        """
        # Set up provider and model
        self.provider = provider or os.getenv("LLM_PROVIDER", LLMProvider.OPENAI)
        if isinstance(self.provider, str):
            try:
                self.provider = LLMProvider(self.provider.lower())
            except ValueError:
                self.provider = LLMProvider.CUSTOM
                logger.warning(f"Unknown provider '{provider}', using as custom provider")
        
        # Set up model based on provider if not specified
        self.model = model or self._get_default_model()
        
        # Set up API credentials
        self.api_key = api_key or self._get_api_key()
        self.api_base = api_base or self._get_api_base()
        
        # Configure litellm
        self._configure_litellm()
        
        # Set up logging directory
        self.tmp_folder = os.getenv("TMP_FOLDER", "tmp")
        self.llm_folder = os.getenv("TMP_LLM_FOLDER", "llm")
        self.log_base_path = pathlib.Path(self.tmp_folder) / self.llm_folder
        
    def _get_default_model(self) -> str:
        """Get the default model based on the provider."""
        provider_model_map = {
            LLMProvider.OPENAI: os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview"),
            LLMProvider.ANTHROPIC: os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229"),
            LLMProvider.OLLAMA: os.getenv("OLLAMA_MODEL", "llama3"),
            LLMProvider.LLAMA_CPP: os.getenv("LLAMA_CPP_MODEL", "llama3"),
            LLMProvider.LLMSTUDIO: os.getenv("LLMSTUDIO_MODEL", "default"),
            LLMProvider.CUSTOM: os.getenv("CUSTOM_MODEL", "default"),
        }
        return provider_model_map.get(self.provider, "gpt-4-turbo-preview")
    
    def _get_api_key(self) -> Optional[str]:
        """Get the API key based on the provider."""
        provider_key_map = {
            LLMProvider.OPENAI: os.getenv("OPENAI_API_KEY"),
            LLMProvider.ANTHROPIC: os.getenv("ANTHROPIC_API_KEY"),
            LLMProvider.OLLAMA: None,  # Ollama doesn't require an API key
            LLMProvider.LLAMA_CPP: None,  # Local deployment
            LLMProvider.LLMSTUDIO: os.getenv("LLMSTUDIO_API_KEY"),
            LLMProvider.CUSTOM: os.getenv("CUSTOM_API_KEY"),
        }
        return provider_key_map.get(self.provider)
    
    def _get_api_base(self) -> Optional[str]:
        """Get the API base URL based on the provider."""
        provider_base_map = {
            LLMProvider.OPENAI: os.getenv("OPENAI_API_BASE"),
            LLMProvider.ANTHROPIC: os.getenv("ANTHROPIC_API_BASE"),
            LLMProvider.OLLAMA: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            LLMProvider.LLAMA_CPP: os.getenv("LLAMA_CPP_BASE_URL", "http://localhost:8000"),
            LLMProvider.LLMSTUDIO: os.getenv("LLMSTUDIO_BASE_URL", "http://localhost:8000"),
            LLMProvider.CUSTOM: os.getenv("CUSTOM_API_BASE"),
        }
        return provider_base_map.get(self.provider)
    
    def _configure_litellm(self) -> None:
        """Configure litellm based on the provider."""
        try:
            # Set API keys in litellm
            if self.provider == LLMProvider.OPENAI and self.api_key:
                litellm.openai_key = self.api_key
            elif self.provider == LLMProvider.ANTHROPIC and self.api_key:
                litellm.anthropic_key = self.api_key
            
            # Set custom API base if provided
            if self.api_base:
                if self.provider == LLMProvider.OPENAI:
                    litellm.openai_base_url = self.api_base
                elif self.provider == LLMProvider.ANTHROPIC:
                    litellm.anthropic_base_url = self.api_base
                elif self.provider == LLMProvider.OLLAMA:
                    litellm.ollama_base_url = self.api_base
            
            logger.info(f"LLM client configured for provider: {self.provider}, model: {self.model}")
        except Exception as e:
            logger.error(f"Error configuring litellm: {str(e)}")
            
    def _log_llm_call(self, model: str, params: Dict[str, Any], response: Any) -> None:
        """Log LLM call to a file.
        
        Args:
            model: The model name used for the call
            params: The parameters sent to the LLM
            response: The response received from the LLM
        """
        try:
            # Create timestamp for the log file
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            
            # Create directory structure if it doesn't exist
            model_dir = self.log_base_path / f"{self.provider}_{model}"
            model_dir.mkdir(parents=True, exist_ok=True)
            
            # Create log file path
            log_file_path = model_dir / f"{timestamp}.txt"
            
            # Prepare log content
            log_content = {
                "timestamp": datetime.datetime.now().isoformat(),
                "provider": str(self.provider),
                "model": model,
                "params": params,
                "response": self._format_response_for_logging(response)
            }
            
            # Write to file
            with open(log_file_path, 'w', encoding='utf-8') as f:
                json.dump(log_content, f, indent=2, default=str)
                
            logger.info(f"LLM call logged to {log_file_path}")
        except Exception as e:
            logger.error(f"Error logging LLM call: {str(e)}")
            
    def _format_response_for_logging(self, response: Any) -> Dict[str, Any]:
        """Format the response object for logging.
        
        Args:
            response: The response from the LLM
            
        Returns:
            A dictionary representation of the response suitable for logging
        """
        if isinstance(response, LLMResponse):
            return {
                "content": response.content,
                "tool_calls": response.tool_calls,
                "role": response.role
            }
        elif isinstance(response, ModelResponse):
            # Handle litellm ModelResponse
            return {
                "content": response.choices[0].message.content if response.choices else "",
                "tool_calls": self._extract_tool_calls_from_litellm(response),
                "role": response.choices[0].message.role if response.choices else "assistant",
                "model": response.model,
                "usage": response.usage._asdict() if hasattr(response, "usage") else None
            }
        elif hasattr(response, "choices") and len(response.choices) > 0:
            # Handle other response types with choices
            message = response.choices[0].message
            return {
                "content": message.content,
                "tool_calls": self._extract_tool_calls(message),
                "role": message.role
            }
        else:
            # For cases where we can't easily format the response
            return {"raw": str(response)}
            
    def _extract_tool_calls_from_litellm(self, response: ModelResponse) -> Optional[List[Dict[str, Any]]]:
        """Extract tool calls from a litellm ModelResponse."""
        if not response or not hasattr(response, 'choices') or not response.choices:
            return None
            
        # For streaming responses, the structure is different
        if hasattr(response.choices[0], 'delta') and hasattr(response.choices[0].delta, 'tool_calls'):
            tool_calls = []
            delta_tool_calls = response.choices[0].delta.tool_calls
            if delta_tool_calls:
                for tc in delta_tool_calls:
                    if hasattr(tc, "function"):
                        tool_calls.append({
                            "name": tc.function.name if hasattr(tc.function, 'name') else "",
                            "arguments": json.loads(tc.function.arguments) if hasattr(tc.function, 'arguments') and isinstance(tc.function.arguments, str) else {}
                        })
            return tool_calls if tool_calls else None
            
        # For non-streaming responses
        if hasattr(response.choices[0], 'message') and hasattr(response.choices[0].message, 'tool_calls'):
            message_tool_calls = response.choices[0].message.tool_calls
            if not message_tool_calls:
                return None
                
            tool_calls = []
            for tc in message_tool_calls:
                if hasattr(tc, "function"):
                    tool_calls.append({
                        "name": tc.function.name,
                        "arguments": json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments
                    })
            return tool_calls if tool_calls else None
            
        return None
        
    def _extract_tool_calls(self, message) -> Optional[List[Dict[str, Any]]]:
        """Extract tool calls from a message object."""
        if not hasattr(message, "tool_calls") or not message.tool_calls:
            return None
            
        return [{
            "name": tc.function.name,
            "arguments": json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments
        } for tc in message.tool_calls]

    def call_llm(
        self,
        messages: List[Dict[str, str]],
        stream: bool = True,
        function_schemas: Optional[List[Dict]] = None,
        model: Optional[str] = None,
    ) -> Union[LLMResponse, Generator[str, None, LLMResponse]]:
        """Call the LLM with the given messages.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            stream: Whether to stream the response
            function_schemas: Optional list of function schemas for function calling
            model: Optional model override
            
        Returns:
            Either an LLMResponse object or a generator yielding content chunks and finally an LLMResponse
        """
        # Use provided model or default
        model_to_use = model or self.model
        
        logger.info(f"Calling LLM with provider: {self.provider}, model: {model_to_use}")
        logger.info(f"Stream mode: {stream}")
        logger.info(f"Number of messages: {len(messages)}")
        logger.info(f"Function schemas provided: {bool(function_schemas)}")
        
        # Log messages (excluding potentially sensitive system prompts)
        for msg in messages:
            if msg['role'] != 'system':
                logger.info(f"Message ({msg['role']}): {msg['content'][:100]}...")

        # Prepare parameters for litellm
        params = {
            "model": model_to_use,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1000,
            "stream": stream
        }

        # Add tools if function schemas are provided
        if function_schemas:
            params["tools"] = function_schemas
            logger.info(f"Function schemas: {json.dumps(function_schemas, indent=2)}")

        try:
            logger.info(f"Making LLM API call to {self.provider}...")
            
            # Make the API call using litellm
            response = litellm.completion(**params)
            
            logger.info(f"LLM API call successful")

            if stream:
                return self._handle_streaming_response(response, model_to_use, params)
            else:
                return self._handle_non_streaming_response(response, model_to_use, params)

        except Exception as e:
            logger.error(f"Error in LLM call: {str(e)}", exc_info=True)
            raise
            
    def _handle_streaming_response(self, response, model: str, params: Dict[str, Any]) -> Generator[str, None, LLMResponse]:
        """Handle streaming response from litellm."""
        collected_chunks = []
        collected_content = ""
        
        try:
            for chunk in response:
                # Extract content from the chunk
                if hasattr(chunk, "choices") and chunk.choices:
                    # For streaming, we need to check delta instead of message
                    if hasattr(chunk.choices[0], 'delta'):
                        delta = chunk.choices[0].delta
                        
                        # Handle content if present
                        if hasattr(delta, "content") and delta.content:
                            collected_content += delta.content
                            yield delta.content
                
                # Save the chunk for later processing
                collected_chunks.append(chunk)
            
            # After stream ends, process the complete response
            logger.info(f"Stream complete. Collected {len(collected_chunks)} chunks")
            
            # Create the final response
            llm_response = LLMResponse(
                content=collected_content,
                tool_calls=None,  # We'll set this later if needed
                role="assistant"
            )
            
            # Check if any chunks have tool calls
            for chunk in collected_chunks:
                tool_calls = self._extract_tool_calls_from_litellm(chunk)
                if tool_calls:
                    llm_response.tool_calls = tool_calls
                    break
            
            # Log the LLM call after completion
            self._log_llm_call(model, params, llm_response)
            
            yield llm_response
            
        except Exception as e:
            logger.error(f"Error in stream processing: {str(e)}", exc_info=True)
            raise
            
    def _handle_non_streaming_response(self, response, model: str, params: Dict[str, Any]) -> LLMResponse:
        """Handle non-streaming response from litellm."""
        try:
            # Extract content from the response
            content = ""
            if hasattr(response, 'choices') and response.choices:
                if hasattr(response.choices[0], 'message') and hasattr(response.choices[0].message, 'content'):
                    content = response.choices[0].message.content or ""
            
            # Extract tool calls from the response
            tool_calls = self._extract_tool_calls_from_litellm(response)
            
            # Create the response object
            llm_response = LLMResponse(
                content=content,
                tool_calls=tool_calls,
                role="assistant"
            )
            
            # Log the LLM call
            self._log_llm_call(model, params, llm_response)
            
            return llm_response
            
        except Exception as e:
            logger.error(f"Error processing non-streaming response: {str(e)}", exc_info=True)
            raise 