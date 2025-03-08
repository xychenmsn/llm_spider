#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for multi-provider LLM client
"""

import os
from dotenv import load_dotenv
from llm.llm_client import LLMClient, LLMProvider

# Load environment variables
load_dotenv()

def test_openai():
    """Test OpenAI provider"""
    print("\n=== Testing OpenAI Provider ===")
    client = LLMClient(provider=LLMProvider.OPENAI)
    response = client.call_llm([{'role': 'user', 'content': 'Say hello world'}], stream=False)
    print(f"Response: {response.content}")
    print(f"Provider: {client.provider}")
    print(f"Model: {client.model}")

def test_anthropic():
    """Test Anthropic provider"""
    print("\n=== Testing Anthropic Provider ===")
    # Skip if no API key
    if not os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") == "your_anthropic_api_key_here":
        print("Skipping Anthropic test: No API key provided")
        return
        
    client = LLMClient(provider=LLMProvider.ANTHROPIC)
    response = client.call_llm([{'role': 'user', 'content': 'Say hello world'}], stream=False)
    print(f"Response: {response.content}")
    print(f"Provider: {client.provider}")
    print(f"Model: {client.model}")

def test_ollama():
    """Test Ollama provider"""
    print("\n=== Testing Ollama Provider ===")
    # Check if Ollama is running
    import requests
    try:
        requests.get(os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"), timeout=1)
    except:
        print("Skipping Ollama test: Ollama server not running")
        return
        
    client = LLMClient(provider=LLMProvider.OLLAMA)
    response = client.call_llm([{'role': 'user', 'content': 'Say hello world'}], stream=False)
    print(f"Response: {response.content}")
    print(f"Provider: {client.provider}")
    print(f"Model: {client.model}")

def test_streaming():
    """Test streaming with default provider"""
    print("\n=== Testing Streaming ===")
    client = LLMClient()  # Use default provider from .env
    print(f"Using provider: {client.provider}")
    print(f"Using model: {client.model}")
    
    generator = client.call_llm([{'role': 'user', 'content': 'Count from 1 to 5'}], stream=True)
    
    content = ""
    for chunk in generator:
        if isinstance(chunk, str):
            content += chunk
            print(f"Received chunk: {chunk}", end="", flush=True)
        else:
            # This is the final LLMResponse object
            print(f"\nFinal response object received")
            
    print(f"\nFinal content: {content}")

def test_function_calling():
    """Test function calling with default provider"""
    print("\n=== Testing Function Calling ===")
    client = LLMClient()  # Use default provider from .env
    print(f"Using provider: {client.provider}")
    print(f"Using model: {client.model}")
    
    # Define a simple function schema
    function_schemas = [
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
    
    response = client.call_llm(
        [{'role': 'user', 'content': 'What\'s the weather like in San Francisco?'}],
        stream=False,
        function_schemas=function_schemas
    )
    
    print(f"Response content: {response.content}")
    print(f"Tool calls: {response.tool_calls}")

if __name__ == "__main__":
    print("Testing multi-provider LLM client")
    
    # Test default provider (from .env)
    print("\n=== Testing Default Provider ===")
    default_client = LLMClient()
    print(f"Default provider: {default_client.provider}")
    print(f"Default model: {default_client.model}")
    
    # Run provider-specific tests
    test_openai()
    test_anthropic()
    test_ollama()
    
    # Test streaming and function calling
    test_streaming()
    test_function_calling() 