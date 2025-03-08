#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - Fetch Webpage Function

This module provides a function to fetch the HTML content of a webpage.
"""

import logging
from typing import Dict, Any

from llm.function import Function

# Set up logging
logger = logging.getLogger(__name__)


class FetchWebpage(Function):
    """Function to fetch the HTML content of a webpage."""
    
    name = "fetch_webpage"
    description = "Fetch the HTML content of a webpage"
    parameters = {
        "url": {
            "type": "string",
            "description": "The URL of the webpage to fetch"
        }
    }
    required_parameters = {"url"}
    
    def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the function with the given arguments."""
        url = args.get("url", "")
        if not url:
            return {"error": "URL is required"}
        
        # Get the parser_designer from context
        parser_designer = self.context.get("parser_designer")
        if not parser_designer:
            return {"error": "Parser designer not initialized"}
        
        logger.info(f"Fetching webpage: {url}")
        
        # Call the actual implementation
        return parser_designer._fetch_webpage(url) 