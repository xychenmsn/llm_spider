#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for the new Pydantic-based Function implementation
"""

import json
from llm.function_manager import FunctionManager
from llm.functions import GetWeather

def test_function_schema():
    """Test that the function schema is generated correctly."""
    # Get the schema for the GetWeather function
    schema = GetWeather.get_schema()
    
    print("Function Schema:")
    print(json.dumps(schema, indent=2))
    
    # Verify the schema has the expected structure
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "get_weather"
    assert "parameters" in schema["function"]
    assert "properties" in schema["function"]["parameters"]
    assert "location" in schema["function"]["parameters"]["properties"]
    assert "unit" in schema["function"]["parameters"]["properties"]
    
    print("Schema validation passed!")

def test_function_execution():
    """Test that the function executes correctly."""
    # Create an instance of the function
    function = GetWeather()
    
    # Test with valid inputs
    print("\nTesting with valid inputs:")
    result = function(location="San Francisco, CA", unit="celsius")
    print(json.dumps(result, indent=2))
    
    # Verify the result has the expected structure
    assert "location" in result
    assert "temperature" in result
    assert "conditions" in result
    assert "humidity" in result
    assert "timestamp" in result
    
    # Test with invalid unit
    print("\nTesting with invalid unit:")
    try:
        result = function(location="San Francisco, CA", unit="kelvin")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Got expected error: {str(e)}")
    
    # Test with missing required parameter
    print("\nTesting with missing required parameter:")
    try:
        result = function(unit="celsius")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Got expected error: {str(e)}")
    
    print("Execution tests passed!")

def test_function_manager():
    """Test that the function works with the FunctionManager."""
    # Get all function schemas
    schemas = FunctionManager.get_all_schemas()
    
    # Find the get_weather schema
    get_weather_schema = None
    for schema in schemas:
        if schema["function"]["name"] == "get_weather":
            get_weather_schema = schema
            break
    
    print("\nFunction Manager Schema:")
    print(json.dumps(get_weather_schema, indent=2))
    
    # Create a function manager instance
    manager = FunctionManager()
    
    # Execute the function through the manager
    print("\nExecuting through Function Manager:")
    result = manager.execute_function("get_weather", {"location": "New York, NY", "unit": "fahrenheit"})
    print(json.dumps(result, indent=2))
    
    # Test tool call execution
    print("\nExecuting through Tool Call:")
    tool_call = {
        "name": "get_weather",
        "arguments": {
            "location": "London, UK",
            "unit": "celsius"
        }
    }
    result = FunctionManager.execute_tool_call(tool_call)
    print(json.dumps(result, indent=2))
    
    print("Function Manager tests passed!")

if __name__ == "__main__":
    print("Testing Pydantic-based Function implementation")
    
    # Run the tests
    test_function_schema()
    test_function_execution()
    test_function_manager() 