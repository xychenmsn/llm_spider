#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - Function Base Class

This module provides the Function base class for creating functions that can be called by an LLM.
"""

import logging
from typing import Dict, Any, ClassVar, Set
from abc import ABC, abstractmethod

# Set up logging
logger = logging.getLogger(__name__)


class Function(ABC):
    """Base class for all functions that can be called by an LLM."""
    
    # Class variables to be overridden by subclasses
    name: ClassVar[str] = ""
    description: ClassVar[str] = ""
    parameters: ClassVar[Dict[str, Any]] = {}
    required_parameters: ClassVar[Set[str]] = set()
    
    def __init__(self, **kwargs):
        """Initialize with any context needed for execution."""
        self.context = kwargs
    
    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Generate the function schema for LLM function calling."""
        return {
            "type": "function",
            "function": {
                "name": cls.name,
                "description": cls.description,
                "parameters": {
                    "type": "object",
                    "properties": cls.parameters,
                    "required": list(cls.required_parameters)
                }
            }
        }
    
    @abstractmethod
    def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the function with the given arguments."""
        pass 