#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - Function Manager

This module provides the FunctionManager class for managing and executing functions.
"""

import json
import logging
import inspect
import importlib
import pkgutil
import os
from typing import Dict, Any, List, Type, Optional, ClassVar, Set, Callable

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Configure console handler if not already configured
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


class FunctionManager:
    """
    Manages function registration and execution.
    
    This class provides a unified interface for registering and executing functions.
    Functions are automatically registered when imported.
    """
    
    # Class-level registry of functions
    _functions: Dict[str, Type["Function"]] = {}
    _initialized = False
    
    def __init__(self, **kwargs):
        """Initialize with any context needed for execution."""
        self.context = kwargs
        logger.info("FunctionManager initialized")
        
        # Ensure functions are loaded
        if not FunctionManager._initialized:
            FunctionManager.discover_functions()
    
    @classmethod
    def register(cls, function_class: Type["Function"]) -> Type["Function"]:
        """
        Register a function class.
        
        This can be used as a decorator, but functions are also automatically registered
        when they are imported, so explicit registration is usually not necessary.
        """
        function_name = function_class.name
        if function_name in cls._functions:
            logger.warning(f"Function {function_name} already registered. Overwriting.")
        cls._functions[function_name] = function_class
        logger.info(f"Registered function: {function_name}")
        return function_class
    
    @classmethod
    def get_function(cls, function_name: str) -> Optional[Type["Function"]]:
        """Get a function class by name."""
        return cls._functions.get(function_name)
    
    @classmethod
    def get_all_functions(cls) -> Dict[str, Type["Function"]]:
        """Get all registered functions."""
        return cls._functions.copy()
    
    @classmethod
    def get_all_schemas(cls) -> List[Dict[str, Any]]:
        """Get schemas for all registered functions."""
        # Ensure functions are loaded
        if not cls._initialized:
            cls.discover_functions()
        return [func.get_schema() for func in cls._functions.values()]
    
    @classmethod
    def discover_functions(cls):
        """
        Discover and register all functions in the functions package.
        
        This method is called automatically when the FunctionManager is first initialized
        or when get_all_schemas is called.
        
        Files excluded from discovery:
        - __init__.py - Package initialization
        - base.py - Base classes (if exists)
        - template.py - Template for creating new functions
        - README.md - Documentation
        """
        if cls._initialized:
            return
        
        try:
            # Import the functions package
            from llm import functions
            
            # Get the package path
            package_path = os.path.dirname(functions.__file__)
            
            # Files to exclude from discovery
            excluded_files = ['__init__', 'base', 'template']
            
            # Import all modules in the functions package
            for _, module_name, is_pkg in pkgutil.iter_modules([package_path]):
                # Skip excluded files
                if module_name in excluded_files:
                    logger.debug(f"Skipping excluded file: {module_name}.py")
                    continue
                
                # Import the module
                module = importlib.import_module(f"llm.functions.{module_name}")
                
                # Find all Function subclasses in the module
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, functions.Function) and 
                        obj != functions.Function and
                        hasattr(obj, 'name') and
                        obj.name):  # Only register functions with a name
                        
                        # Register the function
                        cls.register(obj)
            
            cls._initialized = True
            logger.info(f"Discovered and registered {len(cls._functions)} functions")
        except Exception as e:
            logger.error(f"Error discovering functions: {str(e)}")
    
    def execute_function(self, function_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a function with the given arguments.
        
        Args:
            function_name: The name of the function to execute
            args: The arguments to pass to the function
            
        Returns:
            The result of the function execution
        """
        function_class = self._functions.get(function_name)
        if not function_class:
            logger.error(f"Function {function_name} not found")
            return {"error": f"Function {function_name} not found"}
        
        try:
            # Create an instance of the function with the context
            function_instance = function_class(**self.context)
            
            # Call the function with the arguments
            return function_instance(**args)
        except Exception as e:
            logger.error(f"Error executing function {function_name}: {str(e)}")
            return {"error": str(e)}
    
    @classmethod
    def execute_tool_call(cls, tool_call: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute a tool call from an LLM.
        
        Args:
            tool_call: The tool call from the LLM
            context: Optional context to pass to the function
            
        Returns:
            The result of the function execution
        """
        function_name = tool_call.get("name")
        arguments = tool_call.get("arguments", {})
        
        function_class = cls._functions.get(function_name)
        if not function_class:
            logger.error(f"Function {function_name} not found")
            return {"error": f"Function {function_name} not found"}
        
        try:
            # Create an instance of the function with the context
            function_instance = function_class(**(context or {}))
            
            # Call the function with the arguments
            return function_instance(**arguments)
        except Exception as e:
            logger.error(f"Error executing function {function_name}: {str(e)}")
            return {"error": str(e)}


# Function to get all function schemas for LLM function calling
def get_function_schemas() -> List[Dict[str, Any]]:
    """Get schemas for all registered functions."""
    return FunctionManager.get_all_schemas() 