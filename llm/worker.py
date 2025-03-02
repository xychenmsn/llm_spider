#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - LLM Worker

This module provides the worker class for asynchronous LLM calls using Qt.
"""

import logging
from typing import List, Dict, Any, Optional

from PySide6.QtCore import QObject, Signal, Slot

from .llm_client import LLMClient

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

class LLMWorker(QObject):
    """Worker class for asynchronous LLM calls using Qt signals."""
    
    # Signals
    response_received = Signal(object)  # For complete response
    chunk_received = Signal(str)  # For streaming chunks
    function_call_received = Signal(object, object)  # For function calls
    error_occurred = Signal(str)  # For errors
    finished = Signal()  # When the operation is complete
    
    def __init__(self, parent=None):
        """Initialize the worker with Qt parent and LLM client."""
        super().__init__(parent)
        self.is_running = False
        self.llm_client = LLMClient()
    
    @Slot(object, bool)
    def call_llm(self, messages: List[Dict[str, str]], stream: bool = True, function_schemas: Optional[List[Dict]] = None, model: str = "gpt-4-turbo-preview"):
        """Call the LLM with the given messages using Qt signals for communication.
        
        Args:
            messages: List of message dictionaries
            stream: Whether to stream the response
            function_schemas: Optional list of function schemas
            model: The model to use
        """
        self.is_running = True
        
        try:
            # Define callbacks for the LLMClient
            def on_stream(chunk: str):
                self.chunk_received.emit(chunk)
            
            def on_tool_call(function_name: str, function_args: Dict):
                self.function_call_received.emit(function_name, function_args)
            
            # Call the LLM client with appropriate callbacks
            response = self.llm_client.call_llm(
                messages=messages,
                stream=stream,
                function_schemas=function_schemas,
                model=model,
                callback_stream=on_stream if stream else None,
                callback_tool_call=on_tool_call
            )
            
            if stream:
                # Process the generator
                for _ in response:
                    pass  # Chunks are handled by the callback
            else:
                # Emit the complete response
                self.response_received.emit(response)
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error in LLM call: {error_msg}")
            self.error_occurred.emit(error_msg)
        
        finally:
            self.is_running = False
            logger.info("LLM call finished")
            self.finished.emit() 