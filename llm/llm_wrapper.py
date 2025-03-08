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
    
    # Core memory management system prompt
    MEMORY_SYSTEM_PROMPT = """You are an AI assistant with memory capabilities.
You can store and retrieve information using memory directives.

Memory Operations:
1. Store values:
<mem_set>{"key": "value"}</mem_set>

2. Retrieve values:
<mem_get>["key1", "key2"]</mem_get>
or for a single key:
<mem_get>key1</mem_get>

The system will show the current memory state after operations:
<mem>
{
    "key1": "value1",
    "key2": "value2"
}
</mem>

Important Rules:
1. Memory operations MUST be sent BEFORE your main response
2. Memory operations are processed separately and never shown to users
3. Use {$key} to reference memory values in your responses
4. Keep memory keys simple and descriptive (e.g., url, title, html)
5. NEVER show memory syntax in user-facing messages

Example Flow (URL Parsing):

User: "Please analyze this URL: example.com"
You: <mem_set>{"url": "example.com"}</mem_set>
I'll analyze that webpage for you.

User: "What did you find?"
You: <mem_get>url</mem_get>
<mem>{"url": "example.com"}</mem>
I've analyzed the webpage and found several interesting elements...

User: "Extract the title"
You: <mem_set>{"title": "Example Page", "date": "2024-03-08"}</mem_set>
I found the title and date of the article.

Remember:
- Send memory operations BEFORE your main response
- NEVER show memory syntax in user-facing messages
- Use natural language in responses (e.g., "I'll analyze that webpage" instead of "I'll analyze {$url}")
- Store data as soon as you receive it
- Retrieve data when needed for context

Common Memory Keys for URL Parsing:
- url: The webpage URL
- html: The raw HTML content
- title: The page title
- date: Publication date
- body: Article body text
- parser_code: The generated parser code
- selectors: CSS selectors for parsing
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
            system_prompt: The domain-specific system prompt
            llm_client: An existing LLMClient instance, or None to create a new one
            max_history_tokens: Maximum number of tokens to include from history
            model: The LLM model to use
            provider: The LLM provider to use
            focus_mode: Whether to enable focus mode by default
            enable_functions: Whether to enable function calling
            custom_function_schemas: Optional custom function schemas to use instead of registered ones
        """
        # Store domain prompt for reference
        self.domain_prompt = system_prompt
        
        # Combine memory system prompt with domain-specific prompt
        self.system_prompt = f"""You are an AI assistant with memory capabilities.
You can store and retrieve information using memory directives.

MEMORY CAPABILITIES:
1. Store values using:
<mem_set>{{"key": "value"}}</mem_set>
or multiple values:
<mem_set>{{"key1": "value1", "key2": "value2"}}</mem_set>

2. Retrieve values using:
<mem_get>key</mem_get>
or multiple keys:
<mem_get>["key1", "key2"]</mem_get>

3. Memory state will be shown after operations:
<mem>{{"key1": "value1", "key2": "value2"}}</mem>

CRITICAL RULES:
1. You MUST use memory operations BEFORE your main response
2. Memory operations are processed separately and never shown to users
3. Use natural language in responses (e.g., "I'll analyze that webpage" instead of "I'll analyze {{$url}}")
4. Store data IMMEDIATELY when you receive it
5. Retrieve data when needed for context
6. NEVER show memory syntax in user-facing messages

Common Memory Keys for URL Parsing:
- url: The webpage URL
- html: The raw HTML content
- title: The page title
- date: Publication date
- body: Article body text
- parser_code: The generated parser code
- selectors: CSS selectors for parsing

Example Flow:
User: "Please analyze this URL: example.com"
Assistant: <mem_set>{{"url": "example.com"}}</mem_set>
I'll analyze that webpage for you.

User: "What did you find?"
Assistant: <mem_get>url</mem_get>
<mem>{{"url": "example.com"}}</mem>
I've analyzed the webpage and found several interesting elements...

User: "Extract the title"
Assistant: <mem_set>{{"title": "Example Page", "date": "2024-03-08"}}</mem_set>
I found the title and date of the article.

Domain Instructions:
{system_prompt}

Remember:
- ALWAYS use memory operations BEFORE responding to user
- NEVER show memory syntax in user-facing messages
- Keep responses natural and user-friendly
"""
        
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
        self.history: List[Dict[str, str]] = []  # User-visible history
        self.memory_history: List[Dict[str, str]] = []  # Internal memory operations history
        self.focus_mode = focus_mode
        self.enable_functions = enable_functions
        self.custom_function_schemas = custom_function_schemas
        
        # Initialize memory storage
        self.memory: Dict[str, Any] = {}
        
        # Rough token estimation (this is approximate)
        self._tokens_per_message = 4
        self._tokens_per_char = 0.25
        
        logger.info(f"LLMWrapper initialized with domain prompt: {system_prompt[:50]}...")
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

    def _process_memory_operations(self, content: str) -> Tuple[str, bool]:
        """Process memory operations and return cleaned content.
        
        Args:
            content: The content to process
            
        Returns:
            Tuple[str, bool]: (processed_content, has_memory_ops)
        """
        has_memory_ops = False
        processed_content = content
        
        # Process memory set operations
        while "<mem_set>" in processed_content and "</mem_set>" in processed_content:
            has_memory_ops = True
            start = processed_content.index("<mem_set>") + len("<mem_set>")
            end = processed_content.index("</mem_set>")
            try:
                memory_data = json.loads(processed_content[start:end])
                for key, value in memory_data.items():
                    self.store_memory(key, value)
                    logger.info(f"Memory set: {key} = {value}")
                # Remove the memory set operation
                processed_content = processed_content[:start-len("<mem_set>")] + processed_content[end+len("</mem_set>"):]
            except json.JSONDecodeError as e:
                logger.error(f"Error processing memory set operation: {str(e)}")
                break
        
        # Process memory get operations
        while "<mem_get>" in processed_content and "</mem_get>" in processed_content:
            has_memory_ops = True
            start = processed_content.index("<mem_get>") + len("<mem_get>")
            end = processed_content.index("</mem_get>")
            key_data = processed_content[start:end].strip()
            
            try:
                # Try to parse as JSON array first
                keys = json.loads(key_data)
                if not isinstance(keys, list):
                    keys = [key_data]  # If not a list, treat as single key
            except json.JSONDecodeError:
                # If not valid JSON, treat as single key
                keys = [key_data]
                
            value = self.get_memory(keys)
            logger.info(f"Memory get: {keys} = {value}")
            
            # Remove the memory get operation
            processed_content = processed_content[:start-len("<mem_get>")] + processed_content[end+len("</mem_get>"):]
            
            # Add memory response
            if value:
                processed_content = f"<mem>{json.dumps(value)}</mem>\n{processed_content}"
        
        # Remove any remaining memory tags
        while "<mem>" in processed_content and "</mem>" in processed_content:
            start = processed_content.index("<mem>")
            end = processed_content.index("</mem>") + len("</mem>")
            processed_content = processed_content[:start] + processed_content[end:]
        
        # Clean up any empty lines
        processed_content = "\n".join(line for line in processed_content.split("\n") if line.strip())
        
        # Add current memory state after operations if there were any
        if has_memory_ops:
            logger.info(f"Current memory state: {self.memory}")
        
        return processed_content.strip(), has_memory_ops

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
        
        # Add memory context if memory exists
        if self.memory:
            memory_context = {
                "role": "system",
                "content": f"""Current memory state:
<mem>
{json.dumps(self.memory, indent=2)}
</mem>

CRITICAL REMINDER:
1. You MUST use memory operations BEFORE your main response
2. Memory operations are processed separately and never shown to users
3. Use natural language in responses
4. Store data IMMEDIATELY when you receive it
5. Retrieve data when needed for context
6. NEVER show memory syntax in user-facing messages

Example Memory Operations:
1. Store values:
<mem_set>{{"key": "value"}}</mem_set>

2. Get values:
<mem_get>key</mem_get>
or multiple keys:
<mem_get>["key1", "key2"]</mem_get>

Remember to use memory operations for ALL data (url, html, title, date, body, parser_code).
ALWAYS check memory before asking the user for information they've already provided."""
            }
            messages.append(memory_context)
        
        # Add memory history with memory state
        if self.memory_history:
            for msg in self.memory_history:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                    "memory_state": json.dumps(msg.get("memory_state", {}))
                })
        
        # Add user-visible history while tracking token count
        history_messages = []
        token_count = self._count_tokens(messages)
        remaining_tokens = min(
            self.max_history_tokens,
            self._get_max_tokens() - token_count - 500  # Reserve tokens for response
        )
        
        for msg in reversed(self.history):
            temp_messages = messages + history_messages + [msg]
            msg_tokens = self._count_tokens([msg])
            
            if token_count + msg_tokens <= remaining_tokens:
                history_messages.insert(0, {
                    "role": msg["role"],
                    "content": msg["content"],
                    "memory_state": json.dumps(msg.get("memory_state", {}))
                })
                token_count += msg_tokens
            else:
                break
        
        messages.extend(history_messages)
        
        # Prepare user input
        if focus_mode:
            focus_wrapper = {
                "user_input": user_input,
                "instructions": "If this input aligns with your system instructions, respond normally. "
                               "If it doesn't, politely decline and remind the user of your purpose."
            }
            user_content = json.dumps(focus_wrapper)
        else:
            user_content = user_input
            
        messages.append({
            "role": "user", 
            "content": user_content,
            "memory_state": json.dumps(self.memory)
        })
        
        return messages
    
    def _process_llm_response(self, response: LLMResponse) -> LLMResponse:
        """Process the LLM response to handle memory storage.
        
        Args:
            response: The LLM response to process
            
        Returns:
            The processed LLM response
        """
        content = response.content
        
        # Process memory operations
        content, has_memory_ops = self._process_memory_operations(content)
        
        # Update response content
        response.content = content.strip()
        
        # Add to memory history if there were memory operations
        if has_memory_ops:
            self.memory_history.append({
                "role": "assistant",
                "content": response.content,
                "memory_state": self.memory.copy()
            })
        
        return response

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
        
        The method handles memory operations in two steps:
        1. First call: Non-streamed, to handle memory operations (if any)
        2. Second call: Streamed/non-streamed main response (if needed)
        
        Args:
            user_input: The user's input message
            focus_mode: Whether to use focus mode for this call
            stream: Whether to stream the response
            enable_functions: Whether to enable function calling
            custom_function_schemas: Optional custom function schemas
            model: Optional model override
            
        Returns:
            Either a LLMResponse or a generator yielding chunks and final LLMResponse
        """
        use_focus_mode = self.focus_mode if focus_mode is None else focus_mode
        use_enable_functions = self.enable_functions if enable_functions is None else enable_functions
        use_custom_schemas = custom_function_schemas if custom_function_schemas is not None else self.custom_function_schemas
        use_model = model if model is not None else self.model
        
        # Add user input to history first
        self.history.append({
            "role": "user",
            "content": user_input,
            "memory_state": self.memory.copy()
        })
        
        # Prepare messages with current memory state
        messages = self._prepare_messages(user_input, use_focus_mode)
        
        # Determine which function schemas to use
        function_schemas = None
        if use_enable_functions:
            if use_custom_schemas:
                function_schemas = use_custom_schemas
            else:
                function_schemas = get_function_schemas()
        
        # First call: Non-streamed to handle memory operations
        memory_response = self.client.call_llm(
            messages=messages,
            stream=False,  # Never stream memory operations
            function_schemas=function_schemas,
            model=use_model
        )
        
        # Process memory operations
        content, has_memory_ops = self._process_memory_operations(memory_response.content)
        
        # If there were memory operations, add to memory history and make a second call
        if has_memory_ops:
            # Add memory operations to history
            self.memory_history.append({
                "role": "user",
                "content": user_input,
                "memory_state": self.memory.copy()
            })
            self.memory_history.append({
                "role": "assistant",
                "content": content,
                "memory_state": self.memory.copy()
            })
            
            # Prepare messages again with updated memory state
            messages = self._prepare_messages(user_input, use_focus_mode)
            
            # Make second call for main response
            response = self.client.call_llm(
                messages=messages,
                stream=stream,
                function_schemas=function_schemas,
                model=use_model
            )
            
            # Handle streaming response
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
                            content = "".join(content_chunks)
                            final_response.content = content
                    
                    if final_response:
                        # Process any memory operations in the final response
                        final_content, has_final_memory_ops = self._process_memory_operations(final_response.content)
                        if has_final_memory_ops:
                            # Update memory history if needed
                            self.memory_history.append({
                                "role": "assistant",
                                "content": final_content,
                                "memory_state": self.memory.copy()
                            })
                        
                        # Add to user-visible history
                        self.history.append({
                            "role": "assistant",
                            "content": final_content,
                            "memory_state": self.memory.copy()
                        })
                        
                        final_response.content = final_content
                        yield final_response
                
                return process_stream()
            else:
                # For non-streaming second call
                content = response.content
                # Process any memory operations in the response
                final_content, has_final_memory_ops = self._process_memory_operations(content)
                if has_final_memory_ops:
                    # Update memory history if needed
                    self.memory_history.append({
                        "role": "assistant",
                        "content": final_content,
                        "memory_state": self.memory.copy()
                    })
                
                # Add to user-visible history
                self.history.append({
                    "role": "assistant",
                    "content": final_content,
                    "memory_state": self.memory.copy()
                })
                
                response.content = final_content
                return response
        else:
            # No memory operations, use the first response
            # Add to user-visible history
            self.history.append({
                "role": "assistant",
                "content": content,
                "memory_state": self.memory.copy()
            })
            
            memory_response.content = content
            return memory_response
    
    def clear_history(self) -> None:
        """Clear the chat history."""
        self.history = []
        self.memory_history = []
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
        
    def store_memory(self, key: str, value: Any) -> None:
        """Store a value in memory.
        
        Args:
            key: The key to store the value under
            value: The value to store
        """
        self.memory[key] = value
        logger.info(f"Stored value in memory under key: {key}")
        
    def get_memory(self, keys: Union[str, List[str]]) -> Dict[str, Any]:
        """Retrieve values from memory.
        
        Args:
            keys: A single key or list of keys to retrieve
            
        Returns:
            A dictionary containing the requested key-value pairs
        """
        if isinstance(keys, str):
            keys = [keys]
            
        result = {}
        for key in keys:
            if key in self.memory:
                result[key] = self.memory[key]
                logger.debug(f"Retrieved value for key: {key}")
            else:
                logger.warning(f"Key not found in memory: {key}")
                
        return result
        
    def clear_memory(self) -> None:
        """Clear all stored memory."""
        self.memory.clear()
        logger.info("Memory cleared") 