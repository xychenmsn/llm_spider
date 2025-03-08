#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - Test Function

This module provides a simple test function for testing function calling.
"""

import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from llm.function import Function

# Set up logging
logger = logging.getLogger(__name__)


class TestFunction(Function):
    """A simple test function for testing function calling."""
    
    name = "test_function"
    description = "A simple test function that echoes its input"
    
    class InputModel(BaseModel):
        """Input model for the test function."""
        message: str = Field(
            ..., 
            description="The message to echo back"
        )
        repeat: int = Field(
            1, 
            description="The number of times to repeat the message",
            ge=1,
            le=10
        )
        prefix: Optional[str] = Field(
            None, 
            description="An optional prefix to add to the message"
        )
        tags: Optional[List[str]] = Field(
            None, 
            description="Optional tags to add to the response"
        )
    
    def execute(self, validated_input: InputModel) -> Dict[str, Any]:
        """Execute the function with the given arguments."""
        message = validated_input.message
        repeat = validated_input.repeat
        prefix = validated_input.prefix
        tags = validated_input.tags or []
        
        logger.info(f"Test function called with message: {message}, repeat: {repeat}")
        
        # Process the input
        if prefix:
            message = f"{prefix}: {message}"
            
        # Repeat the message
        repeated_message = " ".join([message] * repeat)
        
        # Return the result
        return {
            "message": repeated_message,
            "repeat_count": repeat,
            "has_prefix": prefix is not None,
            "tags": tags,
            "timestamp": "2023-01-01T00:00:00Z"  # Fixed timestamp for testing
        } 