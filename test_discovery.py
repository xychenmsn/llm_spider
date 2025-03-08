#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script to verify automatic function discovery.
"""

import json
from llm.function_manager import FunctionManager, get_function_schemas

def main():
    """Run the test."""
    print("Testing automatic function discovery...")
    
    # Get all function schemas
    schemas = get_function_schemas()
    
    # Print the number of discovered functions
    print(f"Discovered {len(schemas)} functions:")
    
    # Print the names of the discovered functions
    for schema in schemas:
        function_name = schema["function"]["name"]
        function_desc = schema["function"]["description"]
        print(f"- {function_name}: {function_desc}")
    
    # Verify that template_function is not discovered
    template_function_found = any(schema["function"]["name"] == "template_function" for schema in schemas)
    if template_function_found:
        print("WARNING: template_function was discovered, but it should be excluded!")
    else:
        print("Success: template_function was correctly excluded from discovery.")
    
    # Verify that test_function is discovered
    test_function_found = any(schema["function"]["name"] == "test_function" for schema in schemas)
    if test_function_found:
        print("Success: test_function was correctly discovered.")
    else:
        print("ERROR: test_function was not discovered!")
    
    # Create a FunctionManager instance
    manager = FunctionManager()
    
    # Try to execute the test function
    try:
        result = manager.execute_function("test_function", {"test_param": "test_value"})
        print(f"Function execution result: {json.dumps(result, indent=2)}")
    except Exception as e:
        print(f"Error executing function: {str(e)}")

if __name__ == "__main__":
    main() 