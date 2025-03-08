#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for using Pydantic-based Functions with LLMWrapper and litellm
"""

import json
from llm.llm_wrapper import LLMWrapper
from llm.function_manager import FunctionManager

def test_llm_with_functions():
    """Test that the LLMWrapper works with our Pydantic-based functions."""
    # Create a wrapper with function calling enabled
    wrapper = LLMWrapper(
        system_prompt="You are a helpful assistant that can provide weather information.",
        enable_functions=True
    )
    
    print("LLMWrapper initialized with function calling enabled")
    
    # Get all function schemas
    schemas = FunctionManager.get_all_schemas()
    print(f"Found {len(schemas)} function schemas")
    
    # Print the get_weather schema
    get_weather_schema = None
    for schema in schemas:
        if schema["function"]["name"] == "get_weather":
            get_weather_schema = schema
            break
    
    if get_weather_schema:
        print("\nGet Weather Schema:")
        print(json.dumps(get_weather_schema, indent=2))
    
    # Send a message that should trigger the get_weather function
    print("\nSending message to trigger get_weather function...")
    response = wrapper.chat(
        "What's the weather like in San Francisco?", 
        stream=False
    )
    
    print(f"\nResponse content: {response.content}")
    print(f"Tool calls: {response.tool_calls}")
    
    # If we got a tool call, execute it
    if response.tool_calls:
        print("\nExecuting tool call...")
        tool_call = response.tool_calls[0]
        result = FunctionManager.execute_tool_call(tool_call)
        print(f"Tool call result: {json.dumps(result, indent=2)}")
        
        # Send a follow-up message with the result
        print("\nSending follow-up message with the result...")
        follow_up = wrapper.chat(
            f"The weather information is: {json.dumps(result)}. Can you summarize this for me?",
            stream=False
        )
        
        print(f"\nFollow-up response: {follow_up.content}")
    
    print("\nTest completed successfully!")

if __name__ == "__main__":
    print("Testing LLMWrapper with Pydantic-based Functions")
    
    # Run the test
    test_llm_with_functions() 