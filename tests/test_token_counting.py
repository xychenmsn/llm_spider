#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for token counting and context window management
"""

import json
from llm.llm_wrapper import LLMWrapper
from litellm.utils import token_counter, get_max_tokens

def test_token_counting():
    """Test token counting with litellm."""
    print("\n=== Testing Token Counting ===")
    
    # Create a simple message
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"}
    ]
    
    # Count tokens with litellm
    tokens = token_counter(model="gpt-4", messages=messages)
    print(f"Token count for simple messages: {tokens}")
    
    # Get max tokens for different models
    models = ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo", "claude-3-opus-20240229"]
    for model in models:
        try:
            max_tokens = get_max_tokens(model)
            print(f"Max tokens for {model}: {max_tokens}")
        except Exception as e:
            print(f"Error getting max tokens for {model}: {str(e)}")

def test_wrapper_token_counting():
    """Test token counting in the LLMWrapper."""
    print("\n=== Testing LLMWrapper Token Counting ===")
    
    # Create a wrapper
    wrapper = LLMWrapper(
        system_prompt="You are a helpful assistant that provides concise answers.",
        model="gpt-4"
    )
    
    # Test token counting with different message lengths
    short_message = "Hello, how are you?"
    medium_message = "Can you explain how token counting works in language models? " * 5
    long_message = "This is a very long message that should use a lot of tokens. " * 50
    
    # Prepare messages with different lengths
    short_messages = wrapper._prepare_messages(short_message)
    print(f"Token count for short message: {wrapper._count_tokens(short_messages)}")
    
    medium_messages = wrapper._prepare_messages(medium_message)
    print(f"Token count for medium message: {wrapper._count_tokens(medium_messages)}")
    
    long_messages = wrapper._prepare_messages(long_message)
    print(f"Token count for long message: {wrapper._count_tokens(long_messages)}")
    
    # Check max tokens
    max_tokens = wrapper._get_max_tokens("gpt-4")
    print(f"Max tokens for gpt-4: {max_tokens}")

def test_context_window_management():
    """Test context window management with very long inputs."""
    print("\n=== Testing Context Window Management ===")
    
    # Create a wrapper with a smaller model
    wrapper = LLMWrapper(
        system_prompt="You are a helpful assistant.",
        model="gpt-3.5-turbo"  # Smaller context window
    )
    
    # Create a very long message that exceeds the context window
    very_long_message = "This is a very long message that should exceed the context window. " * 500
    
    print(f"Length of very long message: {len(very_long_message)} characters")
    
    # Send the message and see how it's handled
    print("Sending very long message...")
    response = wrapper.chat(very_long_message, stream=False)
    
    print(f"Response received: {response.content[:100]}...")

if __name__ == "__main__":
    print("Testing token counting and context window management")
    
    # Run the tests
    test_token_counting()
    test_wrapper_token_counting()
    test_context_window_management() 