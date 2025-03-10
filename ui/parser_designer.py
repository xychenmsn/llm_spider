#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - Parser Designer Interface

This module provides a UI for designing URL parsers with LLM assistance.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtCore import Qt, QThread, QTimer
from PySide6.QtGui import QPixmap, QImage

from ui.chat import ChatMessage, ChatHistory, ChatWidget
from llm.worker import LLMWorker
from llm.function_manager import FunctionManager, get_function_schemas
from scraping.utils import fetch_webpage_html, parse_list_page, parse_content_page
from db.models import URLParser
from db.db_client import db_client
from llm.prompts.system_prompts import URL_PARSER_STATE_MACHINE_PROMPT

# Set up logging
logger = logging.getLogger(__name__)


class ParserDesignerWindow(QtWidgets.QDialog):
    """Dialog for designing URL parsers with LLM assistance."""
    
    # Signal to notify when a parser is saved
    parser_saved = QtCore.Signal()
    
    # State constants (kept for reference but state transitions handled by LLM)
    STATE_WAITING_FOR_URL = "S1"
    STATE_FETCHING_HTML = "S2"
    STATE_ANALYZING_CONTENT = "S3"
    STATE_CONFIRMING_EXTRACTION = "S4"
    STATE_CREATING_PARSER = "S5"
    STATE_TESTING_PARSER = "S6"
    STATE_FINAL_CONFIRMATION = "S7"
    STATE_RECOVERY = "RECOVERY"
    
    def __init__(self, parent=None, parser_id=None, url=None):
        super().__init__(parent)
        
        # Make the dialog non-modal
        self.setWindowModality(Qt.NonModal)
        
        self.parser_id = parser_id
        self.parser = None
        self.chat_history = ChatHistory()
        self.url = url
        
        # State and memory management (now controlled by LLM)
        self.current_state = self.STATE_WAITING_FOR_URL
        self.memory = {}
        self.memory_history = []
        
        # Parser data
        self.html_content = None
        self.parser_config = {}
        self.parsed_results = None
        
        # Pending parse request data
        self.pending_parse_url = None
        
        # Set up function manager
        self.function_manager = FunctionManager(parser_designer=self)
        
        # Set up LLM worker in a separate thread
        self.worker_thread = QThread()
        self.llm_worker = LLMWorker()
        self.llm_worker.moveToThread(self.worker_thread)
        
        # Connect signals
        self.llm_worker.response_received.connect(self.on_llm_response)
        self.llm_worker.chunk_received.connect(self.on_llm_chunk)
        self.llm_worker.function_call_received.connect(self.on_function_call)
        self.llm_worker.error_occurred.connect(self.on_llm_error)
        self.llm_worker.finished.connect(self.on_llm_finished)
        
        # Start the worker thread
        self.worker_thread.start()
        
        # Load parser if editing
        if parser_id:
            self.parser = db_client.get_by_id(URLParser, parser_id)
            if self.parser and self.parser.chat_data:
                # Load chat history if available
                try:
                    if isinstance(self.parser.chat_data, str):
                        chat_data = json.loads(self.parser.chat_data)
                    else:
                        chat_data = self.parser.chat_data
                    
                    if "chat_history" in chat_data:
                        self.chat_history = ChatHistory.from_dict(chat_data["chat_history"])
                    if "memory" in chat_data:
                        self.memory = chat_data["memory"]
                    if "state" in chat_data:
                        self.current_state = chat_data["state"]
                except Exception as e:
                    logger.error(f"Failed to load chat history: {str(e)}")
        
        self.setup_ui()
        self.setup_signals()
        
        # Set window properties
        self.setWindowTitle("Parser Designer")
        self.resize(800, 600)
        
        # Initialize chat with system prompt
        self._initialize_chat()
    
    def setup_ui(self):
        """Set up the UI components."""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Header with parser name input
        header_layout = QtWidgets.QHBoxLayout()
        
        # Name input field
        name_layout = QtWidgets.QHBoxLayout()
        name_label = QtWidgets.QLabel("Name:")
        self.name_input = QtWidgets.QLineEdit()
        if self.parser:
            self.name_input.setText(self.parser.name)
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        header_layout.addLayout(name_layout, 2)
        
        header_layout.addStretch()
        
        # Save button
        self.save_button = QtWidgets.QPushButton("Save Parser")
        self.save_button.clicked.connect(self.save_parser)
        header_layout.addWidget(self.save_button)
        
        layout.addLayout(header_layout)
        
        # Toolbar with buttons
        toolbar_layout = QtWidgets.QHBoxLayout()
        
        # URL input field
        url_layout = QtWidgets.QHBoxLayout()
        url_label = QtWidgets.QLabel("URL:")
        self.url_input = QtWidgets.QLineEdit()
        if self.url:
            self.url_input.setText(self.url)
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        toolbar_layout.addLayout(url_layout, 3)
        
        self.browser_button = QtWidgets.QPushButton("Open Browser")
        self.browser_button.clicked.connect(self.open_browser)
        toolbar_layout.addWidget(self.browser_button)
        
        toolbar_layout.addStretch()
        
        layout.addLayout(toolbar_layout)
        
        # Chat widget
        self.chat_widget = ChatWidget()
        self.chat_widget.message_sent.connect(self.on_message_sent)
        layout.addWidget(self.chat_widget)
        
        # Button box
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Close
        )
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Update UI with parser data if editing
        if self.parser:
            # Load chat history
            for message in self.chat_history.messages:
                if message.role != ChatMessage.ROLE_SYSTEM:
                    self.chat_widget.display_message(message)
    
    def setup_signals(self):
        """Set up signal connections."""
        # Connect chat widget signals
        self.chat_widget.message_sent.connect(self.on_message_sent)
        
        # Connect buttons
        if hasattr(self, 'save_button'):
            self.save_button.clicked.connect(self.save_parser)
        
        if hasattr(self, 'test_button'):
            self.test_button.clicked.connect(self.test_parser)
        
        if hasattr(self, 'clear_button'):
            self.clear_button.clicked.connect(self.chat_widget.clear_chat)
    
    def _initialize_chat(self):
        """Initialize the chat with a system prompt."""
        # Use the state machine prompt
        system_prompt = URL_PARSER_STATE_MACHINE_PROMPT
        
        if self.parser:
            # Add parser-specific context
            system_prompt += f"\n\nYou are currently editing the parser named '{self.parser.name}' "
            system_prompt += f"with URL pattern: {self.parser.url_pattern}"
            
            # Load parser data into memory
            try:
                parser_data = json.loads(self.parser.parser)
                self.parser_config = parser_data.get("config", {})
                self.memory.update({
                    "url": self.parser.url_pattern,
                    "parser_code": self.parser_config,
                    "parser_type": parser_data.get("type", "custom_parser")
                })
                
                # If we have a URL, try to fetch HTML and analyze
                if self.url:
                    self._handle_state_transition(self.STATE_FETCHING_HTML)
                else:
                    self._handle_state_transition(self.STATE_CREATING_PARSER)
            except json.JSONDecodeError:
                logger.error("Failed to load parser data")
                self._handle_state_transition(self.STATE_RECOVERY)
        
        self.chat_widget.set_system_prompt(system_prompt)
        
        # If URL is provided, send an initial message to parse it
        if self.url and not self.parser:
            initial_message = (
                f"Welcome to the Parser Designer! I'll help you create a parser for the URL: {self.url}\n\n"
                f"Let me analyze this URL and suggest a parser for it."
            )
            self.chat_widget.receive_message(initial_message)
            
            # Store URL in memory
            self.memory["url"] = self.url
            
            # Send a message to trigger the parsing process
            parse_message = f"Try to parse this URL: {self.url}"
            self.chat_widget.display_message(ChatMessage(ChatMessage.ROLE_USER, parse_message))
            self.chat_widget.history.add_message(ChatMessage(ChatMessage.ROLE_USER, parse_message))
            
            # Transition to fetching HTML state
            self._handle_state_transition(self.STATE_FETCHING_HTML)
            
            # Use a timer to delay the LLM call until after the window is displayed
            QtCore.QTimer.singleShot(100, lambda: self.on_message_sent(parse_message))
        elif not self.chat_history.messages or all(msg.role == ChatMessage.ROLE_SYSTEM for msg in self.chat_history.messages):
            # If no URL and no existing chat history, send a welcome message
            welcome_message = (
                "Welcome to the Parser Designer! I'm here to help you create a URL parser. "
                "Let's start by discussing what kind of URLs you want to parse and what information you want to extract. "
                "You can ask me questions, request code examples, or get suggestions for CSS selectors. "
                "I'll directly generate parser configurations based on the webpage content."
            )
            self.chat_widget.receive_message(welcome_message)
            
            # Start in waiting for URL state
            self._handle_state_transition(self.STATE_WAITING_FOR_URL)
    
    def _process_memory_operations(self, content: str) -> tuple[str, bool]:
        """Process memory operations in LLM response."""
        has_memory_ops = False
        
        # Process memory set operations
        while "<mem_set>" in content and "</mem_set>" in content:
            has_memory_ops = True
            start = content.find("<mem_set>")
            end = content.find("</mem_set>") + len("</mem_set>")
            mem_op = content[start:end]
            try:
                mem_data = json.loads(mem_op[9:-10])  # Extract JSON between tags
                self.memory.update(mem_data)
                self.memory_history.append(("set", mem_data))
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse memory operation: {str(e)}")
            content = content[:start] + content[end:]
        
        # Process memory get operations
        while "<mem_get>" in content and "</mem_get>" in content:
            has_memory_ops = True
            start = content.find("<mem_get>")
            end = content.find("</mem_get>") + len("</mem_get>")
            mem_op = content[start:end]
            key = mem_op[9:-10].strip()  # Extract key between tags
            if key == "all":
                value = json.dumps(self.memory, indent=2)
            else:
                value = str(self.memory.get(key, ""))
            content = content[:start] + value + content[end:]
        
        # Process memory validation
        while "<mem_validate>" in content and "</mem_validate>" in content:
            has_memory_ops = True
            start = content.find("<mem_validate>")
            end = content.find("</mem_validate>") + len("</mem_validate>")
            mem_op = content[start:end]
            try:
                required_keys = json.loads(mem_op[13:-14])  # Extract keys between tags
                missing_keys = [key for key in required_keys if key not in self.memory]
                if missing_keys:
                    content = content[:start] + f"Missing required memory: {', '.join(missing_keys)}" + content[end:]
                else:
                    content = content[:start] + "Memory validation passed" + content[end:]
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse memory validation: {str(e)}")
            content = content[:start] + content[end:]
        
        # Process state changes
        while "<state>" in content and "</state>" in content:
            has_memory_ops = True
            start = content.find("<state>")
            end = content.find("</state>") + len("</state>")
            state_op = content[start:end]
            new_state = state_op[7:-8].strip()  # Extract state between tags
            if new_state != self.current_state:
                self.current_state = new_state
                self.memory_history.append(("state_change", new_state))
            content = content[:start] + f"[State: {new_state}]" + content[end:]
        
        return content, has_memory_ops

    def _validate_state_transition(self, new_state: str) -> bool:
        """Validate if a state transition is allowed based on memory requirements."""
        state_memory_requirements = {
            self.STATE_WAITING_FOR_URL: [],
            self.STATE_FETCHING_HTML: ["url"],
            self.STATE_ANALYZING_CONTENT: ["html"],
            self.STATE_CONFIRMING_EXTRACTION: ["title", "date", "body"],
            self.STATE_CREATING_PARSER: ["html", "title", "date", "body"],
            self.STATE_TESTING_PARSER: ["html", "parser_code"],
            self.STATE_FINAL_CONFIRMATION: ["parsing_result"]
        }
        
        if new_state not in state_memory_requirements:
            return True  # Allow transitions to states without requirements (like RECOVERY)
        
        required_keys = state_memory_requirements[new_state]
        return all(key in self.memory for key in required_keys)

    def _handle_state_transition(self, new_state: str) -> bool:
        """Handle state transition with validation and recovery."""
        if not self._validate_state_transition(new_state):
            logger.warning(f"Invalid state transition to {new_state} - missing required memory")
            self.current_state = self.STATE_RECOVERY
            return False
        
        self.current_state = new_state
        return True

    def on_message_sent(self, message: str):
        """Handle a message sent by the user."""
        # Set the chat widget to processing state
        self.chat_widget.set_processing(True)
        
        # Show a loading indicator
        self.chat_widget.chat_display.append('<div style="color: #999999; font-style: italic;">Assistant is typing...</div>')
        
        # Track if we're receiving streaming chunks
        self.receiving_chunks = False
        
        # Add state information to the message history
        state_message = f"<state>{self.current_state}</state>\n{message}"
        self.chat_widget.history.add_message(ChatMessage(ChatMessage.ROLE_USER, state_message))
        
        # Call LLM worker to get a response
        self.llm_worker.call_llm(self.chat_widget.history.get_openai_messages(), function_schemas=get_function_schemas())
    
    def on_llm_response(self, response):
        """Handle LLM response."""
        # Process memory operations and state changes
        content, has_memory_ops = self._process_memory_operations(response.content)
        
        # Display processed response
        self.chat_widget.receive_message(content)
        
        # Update UI based on current state
        self._update_ui_for_state()
    
    def _update_ui_for_state(self):
        """Update UI elements based on current state."""
        # Enable/disable UI elements based on state
        url_enabled = self.current_state in [self.STATE_WAITING_FOR_URL]
        self.url_input.setEnabled(url_enabled)
        self.browser_button.setEnabled(url_enabled)
        
        # Update save button state
        can_save = self.current_state == self.STATE_FINAL_CONFIRMATION
        self.save_button.setEnabled(can_save)
        
        # Update window title with current state
        self.setWindowTitle(f"Parser Designer - {self.current_state}")
    
    def on_llm_chunk(self, chunk):
        """Handle a chunk of the response from the LLM."""
        # Mark that we're receiving chunks
        self.receiving_chunks = True
        
        # Display the chunk
        self.chat_widget.receive_chunk(chunk)
    
    def on_function_call(self, function_name, function_args):
        """Handle a function call from the LLM."""
        # Add state information to function arguments
        if function_name == "parse_webpage":
            function_args["state"] = self.current_state
        
        # Execute the function through the function manager
        function_response = self.function_manager.execute_function(function_name, function_args)
        
        # Add the function response to the chat history
        self.chat_widget.history.add_message(ChatMessage(
            ChatMessage.ROLE_SYSTEM,
            f"Function {function_name} returned: {json.dumps(function_response)}"
        ))
        
        # Handle state transitions and memory updates based on function response
        if function_name == "parse_webpage":
            if "error" in function_response:
                # Handle error by transitioning to recovery state
                self._handle_state_transition(self.STATE_RECOVERY)
                self.chat_widget.chat_display.append(
                    f'<div style="color: red; padding: 10px; border-radius: 5px; margin: 10px 0;">'
                    f'Error: {function_response["error"]}</div>'
                )
            elif "status" in function_response and function_response["status"] == "success":
                # Display success message if provided
                if "message" in function_response:
                    self.chat_widget.chat_display.append(
                        f'<div style="color: #008800; font-style: italic;">'
                        f'{function_response["message"]}</div>'
                    )
                
                # Handle HTML preview if available
                if "html_preview" in function_response:
                    self.chat_widget.chat_display.append(
                        f'<div style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; margin: 10px 0;">'
                        f'<p><strong>HTML Content Preview:</strong></p>'
                        f'<pre style="white-space: pre-wrap;">{function_response["html_preview"]}</pre>'
                        f'<p>Total length: {function_response.get("html_length", 0)} characters</p>'
                        f'</div>'
                    )
                
                # Handle parsing results if available
                if "parsing_result" in function_response:
                    self.chat_widget.chat_display.append(
                        f'<div style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; margin: 10px 0;">'
                        f'<p><strong>Parsing Result:</strong></p>'
                        f'<pre style="white-space: pre-wrap;">{json.dumps(function_response["parsing_result"], indent=2)}</pre>'
                        f'</div>'
                    )
        
        # Call the LLM again with the updated chat history
        self.llm_worker.call_llm(self.chat_widget.history.get_openai_messages(), function_schemas=get_function_schemas())
    
    def on_llm_error(self, error_message):
        """Handle an error from the LLM."""
        # Remove the "typing" indicator
        self.chat_widget._remove_typing_indicator()
        
        # Display a more helpful error message
        if "authentication" in error_message.lower() or "api key" in error_message.lower():
            self.chat_widget.receive_message("Error: There seems to be an issue with your OpenAI API key. Please check that it's correctly set in your .env file.")
        else:
            self.chat_widget.receive_message(f"Sorry, I encountered an error: {error_message}")
    
    def on_llm_finished(self):
        """Handle the completion of the LLM call."""
        # Set the chat widget to not processing state
        self.chat_widget.set_processing(False)
    
    def _fetch_webpage(self, url: str) -> Dict[str, Any]:
        """Fetch the HTML content of a webpage."""
        if not url:
            url = self.url
        
        if not url:
            return {"error": "No URL provided"}
        
        # Add status message to chat and history
        browser_message = "Opening browser..."
        self.chat_widget.chat_display.append(f'<div style="color: #666666; font-style: italic;">{browser_message}</div>')
        # Add to history as system message
        self.chat_widget.history.add_message(ChatMessage(ChatMessage.ROLE_SYSTEM, browser_message))
        
        try:
            # Create a PlaywrightController instance from fast_spider
            from scraping.playwright_controller import PlaywrightController
            playwright_controller = PlaywrightController()
            
            # Connect signals for status updates
            playwright_controller.debugSignal.connect(self._on_playwright_debug)
            playwright_controller.errorSignal.connect(self._on_playwright_error)
            playwright_controller.completeHtmlSignal.connect(self._on_html_received)
            
            # Start the controller in its own thread
            playwright_controller.start()
            
            # Store the controller for later cleanup
            self.playwright_controller = playwright_controller
            
            # Navigate to the URL asynchronously
            # Give the browser a moment to initialize
            QTimer.singleShot(1000, lambda: playwright_controller.navigate_to_url(url))
            
            # Return a placeholder response - the actual HTML will be processed when the signal is received
            return {
                "url": url,
                "status": "Fetching webpage asynchronously...",
                "message": "Browser opened and navigating to URL. Results will be displayed when available."
            }
        except Exception as e:
            error_message = f"Error starting browser: {str(e)}"
            self.chat_widget.chat_display.append(f'<div style="color: #FF0000;">{error_message}</div>')
            # Add error to history
            self.chat_widget.history.add_message(ChatMessage(ChatMessage.ROLE_SYSTEM, error_message))
            return {"error": error_message}
    
    def _on_playwright_debug(self, message: str):
        """Handle debug messages from the PlaywrightController."""
        self.chat_widget.chat_display.append(f'<div style="color: #666666; font-style: italic;">{message}</div>')
        # Add to history as system message
        self.chat_widget.history.add_message(ChatMessage(ChatMessage.ROLE_SYSTEM, message))
    
    def _on_playwright_error(self, error: str):
        """Handle error messages from the PlaywrightController."""
        self.chat_widget.chat_display.append(f'<div style="color: #FF0000;">{error}</div>')
        # Add to history as system message
        self.chat_widget.history.add_message(ChatMessage(ChatMessage.ROLE_SYSTEM, f"Error: {error}"))
    
    def _on_html_received(self, html: str):
        """Handle the HTML content received from the PlaywrightController."""
        # Store the HTML content
        self.html_content = html
        
        # Update the chat with success message
        html_message = "HTML content retrieved successfully!"
        self.chat_widget.chat_display.append(f'<div style="color: #008800; font-style: italic;">{html_message}</div>')
        # Add to history as system message
        self.chat_widget.history.add_message(ChatMessage(ChatMessage.ROLE_SYSTEM, html_message))
        
        # Close the browser
        closing_message = "Closing browser..."
        self.chat_widget.chat_display.append(f'<div style="color: #666666; font-style: italic;">{closing_message}</div>')
        # Add to history as system message
        self.chat_widget.history.add_message(ChatMessage(ChatMessage.ROLE_SYSTEM, closing_message))
        self.playwright_controller.close_browser()
        
        # Check if we have a pending parse request
        if hasattr(self, 'pending_parse_url') and self.pending_parse_url:
            parsing_message = "Continuing with parsing..."
            self.chat_widget.chat_display.append(f'<div style="color: #666666; font-style: italic;">{parsing_message}</div>')
            # Add to history as system message
            self.chat_widget.history.add_message(ChatMessage(ChatMessage.ROLE_SYSTEM, parsing_message))
            
            # Parse with the pending parser type
            parse_result = self._parse_with_parser(self.pending_parse_url, self.parser_config)
            
            # Add the parse result to the chat history
            self.chat_widget.history.add_message(ChatMessage(
                ChatMessage.ROLE_SYSTEM,
                f"Function parse_with_parser returned: {json.dumps(parse_result)}"
            ))
            
            # Clear the pending parse request
            self.pending_parse_url = None
        elif self.parser_config:
            parsing_message = "Continuing with parsing..."
            self.chat_widget.chat_display.append(f'<div style="color: #666666; font-style: italic;">{parsing_message}</div>')
            # Add to history as system message
            self.chat_widget.history.add_message(ChatMessage(ChatMessage.ROLE_SYSTEM, parsing_message))
            
            # Parse with the configured parser
            parse_result = self._parse_with_parser(self.url, self.parser_config)
            
            # Add the parse result to the chat history
            self.chat_widget.history.add_message(ChatMessage(
                ChatMessage.ROLE_SYSTEM,
                f"Function parse_with_parser returned: {json.dumps(parse_result)}"
            ))
        else:
            # Add the HTML response to the chat history
            html_preview = self.html_content[:1000] + "..." if len(self.html_content) > 1000 else self.html_content
            response_data = {
                'url': self.url,
                'html_preview': html_preview,
                'html_length': len(self.html_content)
            }
            self.chat_widget.history.add_message(ChatMessage(
                ChatMessage.ROLE_SYSTEM,
                f"Function fetch_webpage returned: {json.dumps(response_data)}"
            ))
        
        # Call the LLM again with the updated chat history
        self.llm_worker.call_llm(self.chat_widget.history.get_openai_messages(), function_schemas=get_function_schemas())
    
    def _parse_with_parser(self, url: str, parser_config: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a webpage using the LLM-generated parser."""
        try:
            if not url:
                url = self.url
            
            if not url:
                return {"error": "No URL provided"}
            
            if not self.html_content:
                # Use the asynchronous method to fetch the HTML
                self.chat_widget.chat_display.append('<div style="color: #666666; font-style: italic;">Fetching HTML content first...</div>')
                fetch_result = self._fetch_webpage(url)
                
                # Return a status message - the actual parsing will happen when the HTML is received
                return {
                    "status": "fetching_html",
                    "message": "Fetching HTML content first. Parsing will continue when the content is available."
                }
            
            # Store the parser configuration
            self.parser_config = parser_config
            
            # Determine parser type from the configuration
            parser_type = parser_config.get("type", "")
            
            if parser_type == "list":
                # Parse as a list page
                selector = parser_config.get("selector", "")
                attribute = parser_config.get("attribute", "href")
                
                urls = parse_list_page(self.html_content, selector, attribute)
                self.parsed_results = urls
                
                # Check for errors
                if urls and isinstance(urls[0], str) and urls[0].startswith("Error:"):
                    self.chat_widget.chat_display.append(f'<div style="color: red; padding: 10px; border-radius: 5px; margin: 10px 0;">{urls[0]}</div>')
                    return {"error": urls[0]}
                
                # Display the results in the chat
                self.chat_widget.chat_display.append('<div style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; margin: 10px 0;">')
                self.chat_widget.chat_display.append('<p style="font-weight: bold;">Parsed URLs:</p>')
                self.chat_widget.chat_display.append('<ul>')
                
                for url in urls[:10]:  # Show only the first 10 URLs
                    self.chat_widget.chat_display.append(f'<li>{url}</li>')
                
                if len(urls) > 10:
                    self.chat_widget.chat_display.append(f'<li>... and {len(urls) - 10} more</li>')
                
                self.chat_widget.chat_display.append('</ul>')
                self.chat_widget.chat_display.append('</div>')
                
                return {
                    "parser_type": "list",
                    "url_count": len(urls),
                    "urls": urls[:10],  # Return only the first 10 URLs
                    "has_more": len(urls) > 10
                }
            
            elif parser_type == "content":
                # Parse as a content page
                title_selector = parser_config.get("title_selector", "")
                date_selector = parser_config.get("date_selector", "")
                body_selector = parser_config.get("body_selector", "")
                
                content = parse_content_page(self.html_content, title_selector, date_selector, body_selector)
                self.parsed_results = content
                
                # Check for errors
                if content.get("body", "").startswith("Error:"):
                    self.chat_widget.chat_display.append(f'<div style="color: red; padding: 10px; border-radius: 5px; margin: 10px 0;">{content["body"]}</div>')
                    return {"error": content["body"]}
                
                # Display the results in the chat
                self.chat_widget.chat_display.append('<div style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; margin: 10px 0;">')
                self.chat_widget.chat_display.append('<p style="font-weight: bold;">Parsed Content:</p>')
                
                self.chat_widget.chat_display.append(f'<p><strong>Title:</strong> {content["title"]}</p>')
                self.chat_widget.chat_display.append(f'<p><strong>Date:</strong> {content["date"]}</p>')
                
                # Truncate body if it's too long
                body_preview = content["body"][:500] + "..." if len(content["body"]) > 500 else content["body"]
                self.chat_widget.chat_display.append(f'<p><strong>Body:</strong> {body_preview}</p>')
                
                self.chat_widget.chat_display.append('</div>')
                
                return {
                    "parser_type": "content",
                    "content": {
                        "title": content["title"],
                        "date": content["date"],
                        "body_preview": body_preview,
                        "body_length": len(content["body"])
                    }
                }
            
            else:
                return {"error": f"Unknown parser type: {parser_type}"}
        
        except Exception as e:
            error_msg = f"Error parsing with parser: {str(e)}"
            self.chat_widget.chat_display.append(f'<div style="color: red; padding: 10px; border-radius: 5px; margin: 10px 0;">{error_msg}</div>')
            # Add to history as system message
            self.chat_widget.history.add_message(ChatMessage(ChatMessage.ROLE_SYSTEM, error_msg))
            return {"error": error_msg}
    
    def open_browser(self):
        """Open a browser for testing the parser."""
        # This will be implemented later
        QtWidgets.QMessageBox.information(
            self, "Not Implemented", "Browser functionality will be implemented later."
        )
    
    def save_parser(self):
        """Save the parser to the database."""
        name = self.name_input.text().strip()
        url_pattern = self.url_input.text().strip()
        
        if not name or not url_pattern:
            QtWidgets.QMessageBox.warning(
                self, "Missing Information", "Please provide a name and URL pattern."
            )
            return
        
        # Determine parser type from the configuration
        parser_type = self.parser_config.get("type", "custom_parser")
        
        # Prepare parser data
        parser_data = {
            "type": parser_type,
            "config": self.parser_config,
            "description": self.parser_config.get("description", "")
        }
        
        # Prepare metadata
        meta_data = {
            "last_updated": datetime.now().isoformat(),
            "url": self.url
        }
        
        # Prepare chat data with state and memory
        chat_data = {
            "chat_history": self.chat_widget.history.to_dict(),
            "memory": self.memory,
            "state": self.current_state,
            "memory_history": self.memory_history
        }
        
        if not self.parser:
            # Create a new parser
            self.parser = URLParser(
                name=name,
                url_pattern=url_pattern,
                parser=json.dumps(parser_data),
                meta_data=meta_data,
                chat_data=chat_data
            )
            
            try:
                created_parser = db_client.create(self.parser)
                if created_parser:
                    self.parser = created_parser
                    QtWidgets.QMessageBox.information(
                        self, "Success", f"Parser '{name}' created successfully."
                    )
                    self.accept()  # Close the dialog
                    self.parser_saved.emit()
                else:
                    QtWidgets.QMessageBox.critical(
                        self, "Error", "Failed to create parser."
                    )
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self, "Error", f"Failed to create parser: {str(e)}"
                )
        else:
            # Update existing parser
            self.parser.name = name
            self.parser.url_pattern = url_pattern
            self.parser.parser = json.dumps(parser_data)
            self.parser.meta_data = meta_data
            self.parser.chat_data = chat_data
            
            try:
                updated_parser = db_client.update(self.parser)
                if updated_parser:
                    self.parser = updated_parser
                    QtWidgets.QMessageBox.information(
                        self, "Success", f"Parser '{name}' updated successfully."
                    )
                    self.accept()  # Close the dialog
                    self.parser_saved.emit()
                else:
                    QtWidgets.QMessageBox.critical(
                        self, "Error", "Failed to update parser."
                    )
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self, "Error", f"Failed to update parser: {str(e)}"
                )
    
    def closeEvent(self, event):
        """Handle the window close event."""
        # Log the chat content before closing
        if hasattr(self, 'chat_widget') and self.chat_widget:
            try:
                content = self.chat_widget._get_chat_content()
                if content:
                    self.chat_widget._log_content("=== Chat Session Started ===\n" + content + "\n" + "-"*80 + "\n=== Chat Session Ended ===\n")
            except Exception as e:
                logger.error(f"Failed to log chat content: {str(e)}")
        
        # Clean up the PlaywrightController if it exists
        if hasattr(self, 'playwright_controller') and self.playwright_controller:
            self.playwright_controller.close_browser()
        
        # Clean up the LLM worker resources first
        if hasattr(self, 'llm_worker'):
            self.llm_worker.cleanup()
        
        # Clean up the worker thread
        if self.worker_thread.isRunning():
            self.worker_thread.quit()
            if not self.worker_thread.wait(3000):  # Wait up to 3 seconds
                self.worker_thread.terminate()
                self.worker_thread.wait()
        
        # Accept the event
        event.accept()
    
    def reject(self):
        """Handle the dialog rejection (close button)."""
        # Log the chat content before closing
        if hasattr(self, 'chat_widget') and self.chat_widget:
            try:
                content = self.chat_widget._get_chat_content()
                if content:
                    self.chat_widget._log_content("=== Chat Session Started ===\n" + content + "\n" + "-"*80 + "\n=== Chat Session Ended ===\n")
            except Exception as e:
                logger.error(f"Failed to log chat content: {str(e)}")
        
        # Clean up resources
        if hasattr(self, 'playwright_controller') and self.playwright_controller:
            self.playwright_controller.close_browser()
        
        # Clean up the LLM worker resources first
        if hasattr(self, 'llm_worker'):
            self.llm_worker.cleanup()
        
        # Clean up the worker thread
        if self.worker_thread.isRunning():
            self.worker_thread.quit()
            if not self.worker_thread.wait(3000):  # Wait up to 3 seconds
                self.worker_thread.terminate()
                self.worker_thread.wait()
        
        # Call the parent method
        super().reject()


class NewParserDialog(QtWidgets.QDialog):
    """Dialog for creating a new parser."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Parser")
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the UI components."""
        layout = QtWidgets.QVBoxLayout(self)
        
        form_layout = QtWidgets.QFormLayout()
        
        # Name field
        self.name_input = QtWidgets.QLineEdit()
        form_layout.addRow("Name:", self.name_input)
        
        # URL Pattern field
        self.pattern_input = QtWidgets.QLineEdit()
        form_layout.addRow("URL Pattern:", self.pattern_input)
        
        # Parser field
        self.parser_input = QtWidgets.QLineEdit()
        self.parser_input.setPlaceholderText("custom_parser")
        form_layout.addRow("Parser Type:", self.parser_input)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box) 