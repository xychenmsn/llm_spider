#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - Function Schemas and Execution

This module provides a flexible function system for LLM function calling.
It includes:
1. A base Function class that all functions inherit from
2. Auto-generation of function schemas
3. A registry to collect all available functions
4. A FunctionManager that can execute any registered function

Note: This file is kept for backward compatibility.
The functionality has been moved to the function.py, function_manager.py, and functions package.
"""

# Import from the new locations for backward compatibility
from llm.function import Function
from llm.function_manager import FunctionManager, get_function_schemas
from llm.functions import FetchWebpage, ParseWithParser

# For backward compatibility
__all__ = [
    'Function',
    'FunctionManager',
    'get_function_schemas',
    'FetchWebpage',
    'ParseWithParser',
] 