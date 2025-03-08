#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - Parse With Parser Function

This module provides a function to parse a webpage using an LLM-generated parser.
"""

import logging
from typing import Dict, Any

from llm.function import Function

# Set up logging
logger = logging.getLogger(__name__)


class ParseWithParser(Function):
    """Function to parse a webpage using LLM-generated parser."""
    
    name = "parse_with_parser"
    description = "Parse a webpage using LLM-generated parser"
    parameters = {
        "url": {
            "type": "string",
            "description": "The URL to parse"
        },
        "parser_config": {
            "type": "object",
            "description": "The parser configuration generated by the LLM"
        }
    }
    required_parameters = {"url", "parser_config"}
    
    def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the function with the given arguments."""
        url = args.get("url", "")
        parser_config = args.get("parser_config", {})
        
        if not url:
            return {"error": "URL is required"}
        if not parser_config:
            return {"error": "Parser configuration is required"}
        
        # Get the parser_designer from context
        parser_designer = self.context.get("parser_designer")
        if not parser_designer:
            return {"error": "Parser designer not initialized"}
        
        logger.info(f"Parsing with parser: url={url}")
        
        # Call the actual implementation
        return parser_designer._parse_with_parser(url, parser_config) 