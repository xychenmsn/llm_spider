#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - Parse With Parser Function

This module provides a function to parse HTML content with a parser.
"""

import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from llm.function import Function

# Set up logging
logger = logging.getLogger(__name__)


class ParseWithParser(Function):
    """Function to parse HTML content with a parser."""
    
    name = "parse_with_parser"
    description = "Parse HTML content with a parser"
    
    class InputModel(BaseModel):
        """Input model for the parse_with_parser function."""
        html: str = Field(
            ..., 
            description="The HTML content to parse"
        )
        parser_name: Optional[str] = Field(
            None, 
            description="The name of the parser to use. If not provided, the default parser will be used."
        )
    
    def execute(self, validated_input: InputModel) -> Dict[str, Any]:
        """Execute the function with the given arguments."""
        html = validated_input.html
        parser_name = validated_input.parser_name
        
        # Get the parser_designer from context
        parser_designer = self.context.get("parser_designer")
        if not parser_designer:
            return {"error": "Parser designer not initialized"}
        
        logger.info(f"Parsing HTML with parser: {parser_name or 'default'}")
        
        # Call the actual implementation
        return parser_designer._parse_with_parser(html, parser_name) 