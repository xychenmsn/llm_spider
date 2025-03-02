#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - Function Schemas and Execution

This module provides function schemas and execution for LLM function calling.
"""

import json
import logging
from typing import Dict, Any, List

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Set to INFO level to capture more logs

# Configure console handler if not already configured
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

# Define function schemas for LLM function calling
FUNCTION_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "fetch_webpage",
            "description": "Fetch the HTML content and screenshot of a webpage",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL of the webpage to fetch"
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_list_parser",
            "description": "Create a parser for a list page that extracts URLs",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "CSS selector to find list items"
                    },
                    "attribute": {
                        "type": "string",
                        "description": "Attribute to extract from elements (usually 'href')"
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of how the parser works"
                    }
                },
                "required": ["selector", "attribute", "description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_content_parser",
            "description": "Create a parser for a content page that extracts title, date, and body",
            "parameters": {
                "type": "object",
                "properties": {
                    "title_selector": {
                        "type": "string",
                        "description": "CSS selector to find the title"
                    },
                    "date_selector": {
                        "type": "string",
                        "description": "CSS selector to find the date"
                    },
                    "body_selector": {
                        "type": "string",
                        "description": "CSS selector to find the body content"
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of how the parser works"
                    }
                },
                "required": ["title_selector", "date_selector", "body_selector", "description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "parse_with_parser",
            "description": "Parse a webpage using the created parser",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to parse"
                    },
                    "parser_type": {
                        "type": "string",
                        "description": "Type of parser: 'list' or 'content'"
                    }
                },
                "required": ["url", "parser_type"]
            }
        }
    }
]


class FunctionExecutor:
    """Executes functions called by the LLM."""
    
    def __init__(self, parser_designer=None):
        """Initialize with a reference to the parser designer window."""
        self.parser_designer = parser_designer
        logger.info("FunctionExecutor initialized")
    
    def execute_function(self, function_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a function called by the LLM."""
        logger.info(f"Executing function: {function_name} with args: {json.dumps(args)}")
        
        try:
            if not self.parser_designer:
                error_msg = "Parser designer not initialized"
                logger.error(error_msg)
                return {"error": error_msg}
                
            result = None
            if function_name == "fetch_webpage":
                logger.info(f"Fetching webpage: {args.get('url', '')}")
                result = self.parser_designer._fetch_webpage(args.get("url", ""))
            elif function_name == "create_list_parser":
                logger.info(f"Creating list parser with selector: {args.get('selector', '')}")
                result = self.parser_designer._create_list_parser(
                    args.get("selector", ""),
                    args.get("attribute", "href"),
                    args.get("description", "")
                )
            elif function_name == "create_content_parser":
                logger.info(f"Creating content parser with selectors: title={args.get('title_selector', '')}, date={args.get('date_selector', '')}, body={args.get('body_selector', '')}")
                result = self.parser_designer._create_content_parser(
                    args.get("title_selector", ""),
                    args.get("date_selector", ""),
                    args.get("body_selector", ""),
                    args.get("description", "")
                )
            elif function_name == "parse_with_parser":
                logger.info(f"Parsing with parser: url={args.get('url', '')}, type={args.get('parser_type', '')}")
                result = self.parser_designer._parse_with_parser(
                    args.get("url", ""),
                    args.get("parser_type", "")
                )
            else:
                error_msg = f"Unknown function: {function_name}"
                logger.error(error_msg)
                return {"error": error_msg}
            
            # Log the result (truncate if too large)
            result_str = json.dumps(result)
            if len(result_str) > 500:
                logger.info(f"Function result (truncated): {result_str[:500]}...")
            else:
                logger.info(f"Function result: {result_str}")
                
            return result
        except Exception as e:
            error_msg = f"Error executing function {function_name}: {str(e)}"
            logger.error(error_msg)
            return {"error": str(e)} 