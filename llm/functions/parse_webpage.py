#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - Parse Webpage Function

This module provides a function to parse webpages with state machine control.
"""

import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from llm.function import Function

# Set up logging
logger = logging.getLogger(__name__)


class ParseWebpage(Function):
    """Function to parse webpages with state machine control."""
    
    name = "parse_webpage"
    description = "Parse a webpage with state machine control"
    
    class InputModel(BaseModel):
        """Input model for the parse_webpage function."""
        url: str = Field(
            ..., 
            description="The URL of the webpage to parse"
        )
        state: str = Field(
            ..., 
            description="The current state of the parser (S1-S7 or RECOVERY)"
        )
        action: str = Field(
            ..., 
            description="The action to perform in the current state"
        )
        parser_config: Optional[Dict[str, Any]] = Field(
            None,
            description="The parser configuration to use for parsing"
        )
    
    def execute(self, validated_input: InputModel) -> Dict[str, Any]:
        """Execute the function with the given arguments."""
        url = validated_input.url
        state = validated_input.state
        action = validated_input.action
        parser_config = validated_input.parser_config
        
        # Get the parser_designer from context
        parser_designer = self.context.get("parser_designer")
        if not parser_designer:
            return {"error": "Parser designer not initialized"}
        
        logger.info(f"Processing webpage in state {state} with action {action}")
        
        try:
            # Handle different states
            if state == parser_designer.STATE_WAITING_FOR_URL:
                # Store URL in memory and transition to fetching state
                parser_designer.memory["url"] = url
                parser_designer._handle_state_transition(parser_designer.STATE_FETCHING_HTML)
                return {"status": "success", "message": "URL stored, transitioning to fetch state"}
            
            elif state == parser_designer.STATE_FETCHING_HTML:
                # Fetch HTML content
                if action == "fetch":
                    fetch_result = parser_designer._fetch_webpage(url)
                    return fetch_result
                elif action == "retry":
                    parser_designer.html_content = None
                    fetch_result = parser_designer._fetch_webpage(url)
                    return fetch_result
                else:
                    return {"error": f"Invalid action {action} for state {state}"}
            
            elif state == parser_designer.STATE_ANALYZING_CONTENT:
                # Analyze HTML content
                if not parser_designer.html_content:
                    return {"error": "No HTML content available"}
                
                if action == "analyze":
                    # Store HTML in memory
                    parser_designer.memory["html"] = parser_designer.html_content
                    return {
                        "status": "success",
                        "html_preview": parser_designer.html_content[:1000] + "...",
                        "html_length": len(parser_designer.html_content)
                    }
                else:
                    return {"error": f"Invalid action {action} for state {state}"}
            
            elif state == parser_designer.STATE_CONFIRMING_EXTRACTION:
                # Confirm extracted data
                if not parser_config:
                    return {"error": "No parser configuration provided"}
                
                if action == "confirm":
                    # Store extracted data in memory
                    parser_designer.memory.update({
                        "title": parser_config.get("title_selector", ""),
                        "date": parser_config.get("date_selector", ""),
                        "body": parser_config.get("body_selector", "")
                    })
                    parser_designer._handle_state_transition(parser_designer.STATE_CREATING_PARSER)
                    return {"status": "success", "message": "Extraction confirmed"}
                else:
                    return {"error": f"Invalid action {action} for state {state}"}
            
            elif state == parser_designer.STATE_CREATING_PARSER:
                # Create parser
                if not parser_config:
                    return {"error": "No parser configuration provided"}
                
                if action == "create":
                    # Store parser configuration
                    parser_designer.parser_config = parser_config
                    parser_designer.memory["parser_code"] = parser_config
                    parser_designer._handle_state_transition(parser_designer.STATE_TESTING_PARSER)
                    return {"status": "success", "message": "Parser created"}
                else:
                    return {"error": f"Invalid action {action} for state {state}"}
            
            elif state == parser_designer.STATE_TESTING_PARSER:
                # Test parser
                if not parser_designer.parser_config:
                    return {"error": "No parser configuration available"}
                
                if action == "test":
                    # Test the parser
                    parse_result = parser_designer._parse_with_parser(url, parser_designer.parser_config)
                    if parse_result.get("error"):
                        return parse_result
                    
                    # Store parsing result in memory
                    parser_designer.memory["parsing_result"] = parse_result
                    parser_designer._handle_state_transition(parser_designer.STATE_FINAL_CONFIRMATION)
                    return parse_result
                else:
                    return {"error": f"Invalid action {action} for state {state}"}
            
            elif state == parser_designer.STATE_FINAL_CONFIRMATION:
                # Final confirmation
                if action == "save":
                    # Save the parser
                    parser_designer.save_parser()
                    return {"status": "success", "message": "Parser saved"}
                elif action == "modify":
                    # Go back to creating parser
                    parser_designer._handle_state_transition(parser_designer.STATE_CREATING_PARSER)
                    return {"status": "success", "message": "Returning to parser creation"}
                else:
                    return {"error": f"Invalid action {action} for state {state}"}
            
            elif state == parser_designer.STATE_RECOVERY:
                # Recovery state
                if action == "recover":
                    # Try to recover based on available memory
                    if "parsing_result" in parser_designer.memory:
                        parser_designer._handle_state_transition(parser_designer.STATE_FINAL_CONFIRMATION)
                    elif "parser_code" in parser_designer.memory:
                        parser_designer._handle_state_transition(parser_designer.STATE_TESTING_PARSER)
                    elif "title" in parser_designer.memory:
                        parser_designer._handle_state_transition(parser_designer.STATE_CREATING_PARSER)
                    elif "html" in parser_designer.memory:
                        parser_designer._handle_state_transition(parser_designer.STATE_ANALYZING_CONTENT)
                    elif "url" in parser_designer.memory:
                        parser_designer._handle_state_transition(parser_designer.STATE_FETCHING_HTML)
                    else:
                        parser_designer._handle_state_transition(parser_designer.STATE_WAITING_FOR_URL)
                    return {"status": "success", "message": f"Recovered to state {parser_designer.current_state}"}
                else:
                    return {"error": f"Invalid action {action} for state {state}"}
            
            else:
                return {"error": f"Invalid state: {state}"}
            
        except Exception as e:
            logger.error(f"Error in parse_webpage: {str(e)}")
            return {"error": str(e)} 