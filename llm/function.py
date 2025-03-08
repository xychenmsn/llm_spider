#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - Function Base Class

This module provides the Function base class for creating functions that can be called by an LLM.
Now using Pydantic for validation and schema generation.
"""

import logging
from typing import Dict, Any, ClassVar, Type, Optional, get_type_hints
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field, create_model

# Set up logging
logger = logging.getLogger(__name__)


class Function(ABC):
    """Base class for all functions that can be called by an LLM."""
    
    # Class variables to be overridden by subclasses
    name: ClassVar[str] = ""
    description: ClassVar[str] = ""
    
    # Define the input model as a class variable to be overridden by subclasses
    InputModel: ClassVar[Type[BaseModel]] = None
    
    def __init__(self, **kwargs):
        """Initialize with any context needed for execution."""
        self.context = kwargs
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Generate the function schema for LLM function calling."""
        if not cls.InputModel:
            raise ValueError(f"Function {cls.name} must define an InputModel")
        
        # Get the JSON schema from the Pydantic model
        schema = cls.InputModel.model_json_schema()
        
        return {
            "type": "function",
            "function": {
                "name": cls.name,
                "description": cls.description,
                "parameters": schema
            }
        }
    
    def __call__(self, **kwargs) -> Dict[str, Any]:
        """Execute the function with the given arguments.
        
        This method validates the input using the InputModel before execution.
        """
        if not self.InputModel:
            raise ValueError(f"Function {self.name} must define an InputModel")
            
        try:
            # Validate inputs using the Pydantic model
            validated_input = self.InputModel(**kwargs)
            
            # Call the execute method with validated inputs
            return self.execute(validated_input)
        except Exception as e:
            logger.error(f"Error executing function {self.name}: {str(e)}")
            return {"error": str(e)}
    
    @abstractmethod
    def execute(self, validated_input: BaseModel) -> Dict[str, Any]:
        """Execute the function with validated inputs.
        
        This method should be implemented by subclasses.
        
        Args:
            validated_input: The validated input model
            
        Returns:
            A dictionary with the function result
        """
        pass 