#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - Function Template

This is a template for creating new functions.
Copy this file and rename it to create a new function.
Functions are automatically discovered and registered by the FunctionManager.

NOTE: This file is excluded from automatic discovery and registration.
      It is only meant to be used as a template for creating new functions.
"""

import logging
from typing import Dict, Any

from llm.function import Function

# Set up logging
logger = logging.getLogger(__name__)


class TemplateFunction(Function):
    """
    Template for creating new functions.
    
    This class is not meant to be used directly.
    Copy this file and rename it to create a new function.
    """
    
    # Define the function name, description, parameters, and required parameters
    name = "template_function"
    description = "Template function description"
    parameters = {
        "param1": {
            "type": "string",
            "description": "Description of parameter 1"
        },
        "param2": {
            "type": "object",
            "description": "Description of parameter 2"
        }
    }
    required_parameters = {"param1"}
    
    def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the function with the given arguments."""
        # Get parameters from args
        param1 = args.get("param1", "")
        param2 = args.get("param2", {})
        
        # Validate required parameters
        if not param1:
            return {"error": "param1 is required"}
        
        # Get any context needed for execution
        # example_context = self.context.get("example_context")
        # if not example_context:
        #     return {"error": "Example context not initialized"}
        
        logger.info(f"Executing template function with param1={param1}")
        
        # Implement the function logic
        result = {
            "status": "success",
            "message": f"Executed template function with param1={param1}",
            "data": {
                "param1": param1,
                "param2": param2
            }
        }
        
        return result 