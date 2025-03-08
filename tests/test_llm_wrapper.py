#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for the redesigned LLMWrapper with litellm
"""

import os
from dotenv import load_dotenv
from llm.llm_client import LLMClient, LLMProvider
from llm.llm_wrapper import LLMWrapper

# Load environment variables
load_dotenv()

def test_basic_chat():
    """Test basic chat functionality"""
    print("\n=== Testing Basic Chat ===")
    
    # Create a wrapper with a simple system prompt
    wrapper = LLMWrapper(
        system_prompt="You are a helpful assistant that provides concise answers.",
        focus_mode=False,
        enable_functions=False
    )
    
    # Send a message
    response = wrapper.chat("What is the capital of France?", stream=False)
    
    print(f"Response: {response.content}")
    print(f"History length: {len(wrapper.get_history())}")
    
    # Send a follow-up message
    response = wrapper.chat("What is its population?", stream=False)
    
    print(f"Response: {response.content}")
    print(f"History length: {len(wrapper.get_history())}")
    
    # Print the history
    print("\nChat History:")
    for msg in wrapper.get_history():
        print(f"{msg['role']}: {msg['content'][:50]}...")

def test_focus_mode():
    """Test focus mode functionality"""
    print("\n=== Testing Focus Mode ===")
    
    # Create a wrapper with a specific purpose
    wrapper = LLMWrapper(
        system_prompt="You are a weather assistant. You only answer questions about weather and climate.",
        focus_mode=True
    )
    
    # Send a relevant message
    print("\nRelevant question:")
    response = wrapper.chat("What's the typical weather in Paris in spring?", stream=False)
    print(f"Response: {response.content}")
    
    # Send an irrelevant message
    print("\nIrrelevant question:")
    response = wrapper.chat("What's the capital of France?", stream=False)
    print(f"Response: {response.content}")

def test_function_calling():
    """Test function calling"""
    print("\n=== Testing Function Calling ===")
    
    # Create a wrapper with function calling enabled
    wrapper = LLMWrapper(
        system_prompt="You are a helpful assistant that can use tools.",
        enable_functions=True
    )
    
    # Define a custom function schema
    custom_schemas = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get the current weather in a given location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g. San Francisco, CA"
                        },
                        "unit": {
                            "type": "string",
                            "enum": ["celsius", "fahrenheit"],
                            "description": "The temperature unit to use"
                        }
                    },
                    "required": ["location"]
                }
            }
        }
    ]
    
    # Send a message that should trigger function calling
    response = wrapper.chat(
        "What's the weather like in San Francisco?", 
        stream=False,
        custom_function_schemas=custom_schemas
    )
    
    print(f"Response content: {response.content}")
    print(f"Tool calls: {response.tool_calls}")

def test_streaming():
    """Test streaming functionality"""
    print("\n=== Testing Streaming ===")
    
    # Create a wrapper
    wrapper = LLMWrapper(
        system_prompt="You are a helpful assistant."
    )
    
    # Send a message with streaming
    print("Streaming response:")
    generator = wrapper.chat("Count from 1 to 5", stream=True)
    
    content = ""
    for chunk in generator:
        if isinstance(chunk, str):
            content += chunk
            print(f"{chunk}", end="", flush=True)
    
    print(f"\nFinal content: {content}")
    print(f"History length: {len(wrapper.get_history())}")

def test_provider_switching():
    """Test switching between providers"""
    print("\n=== Testing Provider Switching ===")
    
    # Create a wrapper with OpenAI
    wrapper = LLMWrapper(
        system_prompt="You are a helpful assistant.",
        provider=LLMProvider.OPENAI
    )
    
    print(f"Initial provider: {wrapper.client.provider}")
    
    # Send a message
    response = wrapper.chat("Hello, who are you?", stream=False)
    print(f"OpenAI response: {response.content}")
    
    # Check if Anthropic API key is available
    if os.getenv("ANTHROPIC_API_KEY") and os.getenv("ANTHROPIC_API_KEY") != "your_anthropic_api_key_here":
        # Switch to Anthropic
        wrapper.set_provider(LLMProvider.ANTHROPIC)
        print(f"Switched provider to: {wrapper.client.provider}")
        
        # Send a message
        response = wrapper.chat("Hello, who are you?", stream=False)
        print(f"Anthropic response: {response.content}")
    else:
        print("Skipping Anthropic test: No API key provided")

if __name__ == "__main__":
    print("Testing redesigned LLMWrapper with litellm")
    
    # Run the tests
    test_basic_chat()
    test_focus_mode()
    test_function_calling()
    test_streaming()
    test_provider_switching() 