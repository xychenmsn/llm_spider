#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - Get Weather Function

This module provides a function to get the weather for a location.
This is an example of using the new Pydantic-based Function class.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from llm.function import Function

# Set up logging
logger = logging.getLogger(__name__)


class GetWeather(Function):
    """Function to get the weather for a location."""
    
    name = "get_weather"
    description = "Get the current weather in a given location"
    
    class InputModel(BaseModel):
        """Input model for the get_weather function."""
        location: str = Field(
            ..., 
            description="The city and state, e.g. San Francisco, CA"
        )
        unit: str = Field(
            "celsius", 
            description="The temperature unit to use",
            pattern="^(celsius|fahrenheit)$"
        )
    
    def execute(self, validated_input: InputModel) -> Dict[str, Any]:
        """Get the weather for the specified location.
        
        Args:
            validated_input: The validated input model
            
        Returns:
            A dictionary with the weather information
        """
        # This is a mock implementation
        location = validated_input.location
        unit = validated_input.unit
        
        logger.info(f"Getting weather for {location} in {unit}")
        
        # In a real implementation, you would call a weather API here
        # For now, we'll just return mock data
        weather_data = {
            "location": location,
            "temperature": 22 if unit == "celsius" else 72,
            "conditions": "Sunny",
            "humidity": 45,
            "timestamp": datetime.now().isoformat()
        }
        
        return weather_data 