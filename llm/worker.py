#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - LLM Worker

This module provides the worker class for asynchronous LLM calls using Qt.
"""

import logging
from typing import List, Dict, Any, Optional

from PySide6.QtCore import QObject, Signal, Slot, QThread

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
        self.processor_thread = None
    
    def cleanup(self):
        """Clean up resources and terminate threads."""
        logger.info("Cleaning up LLMWorker resources")
        if self.processor_thread and self.processor_thread.isRunning():
            logger.info("Terminating StreamProcessor thread")
            self.processor_thread.quit()
            if not self.processor_thread.wait(3000):  # Wait up to 3 seconds
                logger.warning("StreamProcessor thread did not terminate gracefully, forcing termination")
                self.processor_thread.terminate()
                self.processor_thread.wait()
        self.is_running = False
    
    @Slot(object, bool)
    def call_llm(self, messages: List[Dict[str, str]], stream: bool = True, function_schemas: Optional[List[Dict]] = None, model: str = "gpt-4-turbo-preview"):
        """Call the LLM with the given messages using Qt signals for communication."""
        self.is_running = True
        logger.info(f"Starting LLM call with stream={stream}")
        
        try:
            if stream:
                logger.info("Initializing streaming response...")
                # Get the generator for streaming response
                generator = self.llm_client.call_llm(
                    messages=messages,
                    stream=True,
                    function_schemas=function_schemas,
                    model=model
                )
                
                # Create a separate thread to process the generator
                class StreamProcessor(QThread):
                    def __init__(self, generator, worker):
                        super().__init__()
                        self.generator = generator
                        self.worker = worker
                    
                    def run(self):
                        try:
                            logger.info("Processing streaming chunks in background thread...")
                            final_response = None
                            for item in self.generator:
                                if isinstance(item, str):
                                    # This is a content chunk
                                    logger.debug(f"Emitting content chunk: {item}")
                                    self.worker.chunk_received.emit(item)
                                else:
                                    # This is the final response
                                    final_response = item
                                    logger.info(f"Final response received: {final_response}")
                                    self.worker.response_received.emit(final_response)
                            
                            # Process any tool calls
                            if final_response and final_response.tool_calls:
                                logger.info(f"Processing {len(final_response.tool_calls)} tool calls")
                                for tool_call in final_response.tool_calls:
                                    logger.info(f"Emitting tool call: {tool_call['name']}")
                                    self.worker.function_call_received.emit(
                                        tool_call['name'],
                                        tool_call['arguments']
                                    )
                        except Exception as e:
                            error_msg = str(e)
                            logger.error(f"Error in stream processing: {error_msg}", exc_info=True)
                            self.worker.error_occurred.emit(error_msg)
                        finally:
                            self.worker.is_running = False
                            logger.info("LLM call finished")
                            self.worker.finished.emit()
                
                # Start the processor thread
                self.processor_thread = StreamProcessor(generator, self)
                self.processor_thread.start()
                
                # Return immediately, don't block the UI thread
                return
            else:
                logger.info("Getting non-streaming response...")
                # Get complete response for non-streaming mode
                response = self.llm_client.call_llm(
                    messages=messages,
                    stream=False,
                    function_schemas=function_schemas,
                    model=model
                )
                
                logger.info(f"Response received: {response}")
                self.response_received.emit(response)
                
                # Process any tool calls
                if response.tool_calls:
                    logger.info(f"Processing {len(response.tool_calls)} tool calls")
                    for tool_call in response.tool_calls:
                        logger.info(f"Emitting tool call: {tool_call['name']}")
                        self.function_call_received.emit(
                            tool_call['name'],
                            tool_call['arguments']
                        )
                
                self.is_running = False
                logger.info("LLM call finished")
                self.finished.emit()
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error in LLM call: {error_msg}", exc_info=True)
            self.error_occurred.emit(error_msg)
            self.is_running = False
            logger.info("LLM call finished with error")
            self.finished.emit() 