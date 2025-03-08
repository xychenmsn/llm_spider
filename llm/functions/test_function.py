#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - Test Function

This is a test function to verify automatic discovery.
"""

import logging
from typing import Dict, Any

from llm.function import Function

# Set up logging
logger = logging.getLogger(__name__)


class TestFunction(Function):
    """Test function to verify automatic discovery."""
    
    name = "test_function"
    description = "A test function to verify automatic discovery"
    parameters = {
        "test_param": {
            "type": "string",
            "description": "A test parameter"
        }
    }
    required_parameters = {"test_param"}
    
    def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the function with the given arguments."""
        test_param = args.get("test_param", "")
        if not test_param:
            return {"error": "test_param is required"}
        
        logger.info(f"Executing test function with test_param={test_param}")
        
        return {
            "status": "success",
            "message": f"Test function executed successfully with test_param={test_param}"
        } 