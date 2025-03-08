#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - Functions Package

This package contains all the functions that can be called by the LLM.
Functions are automatically discovered and registered by the FunctionManager.
"""

# Import the Function base class from the parent package
from llm.function import Function

# Import all functions for registration
from .fetch_webpage import FetchWebpage
from .parse_with_parser import ParseWithParser
from .test_function import TestFunction

# Export all functions
__all__ = [
    'Function',
    'FetchWebpage',
    'ParseWithParser',
    'TestFunction',
] 