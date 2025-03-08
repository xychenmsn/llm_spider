#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for LLM logging functionality
"""

from llm.llm_client import LLMClient
import time

def test_streaming():
    """Test streaming LLM call with logging"""
    client = LLMClient()
    generator = client.call_llm([{'role': 'user', 'content': 'Count from 1 to 5'}], stream=True)
    
    content = ""
    for chunk in generator:
        if isinstance(chunk, str):
            content += chunk
            print(f"Received chunk: {chunk}")
        else:
            # This is the final LLMResponse object
            print(f"Final response object: {chunk}")
            
    print(f"Final content: {content}")

def test_non_streaming():
    """Test non-streaming LLM call with logging"""
    client = LLMClient()
    response = client.call_llm([{'role': 'user', 'content': 'Say hello world'}], stream=False)
    print(f"Response: {response.content}")

if __name__ == "__main__":
    print("Testing non-streaming call:")
    test_non_streaming()
    
    print("\nTesting streaming call:")
    test_streaming() 