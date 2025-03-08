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

# Set up logging
logger = logging.getLogger(__name__)


class ParserDesignerWindow(QtWidgets.QDialog):
    """Dialog for designing URL parsers with LLM assistance."""
    
    # Signal to notify when a parser is saved
    parser_saved = QtCore.Signal()
    
    def __init__(self, parent=None, parser_id=None, url=None):
        super().__init__(parent)
        
        # Make the dialog non-modal
        self.setWindowModality(Qt.NonModal)
        
        self.parser_id = parser_id
        self.parser = None
        self.chat_history = ChatHistory()
        self.url = url
        
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
        system_prompt = (
            "You are an AI assistant helping to design a URL parser. "
            "Your goal is to help the user create a parser that can extract relevant information from URLs. "
            "You can suggest CSS selectors, parsing strategies, and help with implementation details. "
            "Be specific and provide code examples when appropriate. "
            "You have access to functions that can fetch webpage content and parse webpages using your generated parser configurations."
            "\n\nYou should directly generate parser configurations based on the webpage content. "
            "A parser configuration should include a 'type' field ('list' or 'content') and appropriate selectors. "
            "For list parsers, include 'selector' and 'attribute' fields. "
            "For content parsers, include 'title_selector', 'date_selector', and 'body_selector' fields."
        )
        
        if self.parser:
            # Add parser-specific context
            system_prompt += f"\n\nYou are currently editing the parser named '{self.parser.name}' "
            system_prompt += f"with URL pattern: {self.parser.url_pattern}"
        
        self.chat_widget.set_system_prompt(system_prompt)
        
        # If URL is provided, send an initial message to parse it
        if self.url and not self.parser:
            initial_message = (
                f"Welcome to the Parser Designer! I'll help you create a parser for the URL: {self.url}\n\n"
                f"Let me analyze this URL and suggest a parser for it."
            )
            self.chat_widget.receive_message(initial_message)
            
            # Send a message to trigger the parsing process
            parse_message = f"Try to parse this URL: {self.url}"
            self.chat_widget.display_message(ChatMessage(ChatMessage.ROLE_USER, parse_message))
            self.chat_widget.history.add_message(ChatMessage(ChatMessage.ROLE_USER, parse_message))
            
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
    
    def on_message_sent(self, message: str):
        """Handle a message sent by the user."""
        # Set the chat widget to processing state
        self.chat_widget.set_processing(True)
        
        # Show a loading indicator
        self.chat_widget.chat_display.append('<div style="color: #999999; font-style: italic;">Assistant is typing...</div>')
        
        # Track if we're receiving streaming chunks
        self.receiving_chunks = False
        
        # Call LLM worker to get a response
        self.llm_worker.call_llm(self.chat_widget.history.get_openai_messages(), function_schemas=get_function_schemas())
    
    def on_llm_response(self, response_message):
        """Handle the complete response from the LLM."""
        # Remove the "typing" indicator
        self.chat_widget._remove_typing_indicator()
        
        # If we've been receiving chunks, don't display the final message again
        # Just add it to the history
        if hasattr(self, 'receiving_chunks') and self.receiving_chunks:
            # Just add the message to history without displaying it again
            if response_message and hasattr(response_message, 'content') and response_message.content:
                # Finalize the streaming message with the complete content
                self.chat_widget.finalize_streaming_message(response_message.content)
                
                # Add the message to history
                self.chat_widget.history.add_message(ChatMessage(
                    ChatMessage.ROLE_ASSISTANT,
                    response_message.content
                ))
                
                # Reset streaming state
                self.receiving_chunks = False
            return
        
        # If there's content, display it
        if response_message and hasattr(response_message, 'content') and response_message.content:
            self.chat_widget.receive_message(response_message.content)
            
            # Add the assistant's message to the chat history
            self.chat_widget.history.add_message(ChatMessage(
                ChatMessage.ROLE_ASSISTANT,
                response_message.content
            ))
        elif not hasattr(response_message, 'tool_calls') or not response_message.tool_calls:
            # If there's no content and no tool calls, show a generic message
            self.chat_widget.receive_message("I'm processing your request...")
            
            # Add the generic message to the chat history
            self.chat_widget.history.add_message(ChatMessage(
                ChatMessage.ROLE_ASSISTANT,
                "I'm processing your request..."
            ))
    
    def on_llm_chunk(self, chunk):
        """Handle a chunk of the response from the LLM."""
        # Mark that we're receiving chunks
        self.receiving_chunks = True
        
        # Display the chunk
        self.chat_widget.receive_chunk(chunk)
    
    def on_function_call(self, function_name, function_args):
        """Handle a function call from the LLM."""
        # Execute the function
        if function_name == "parse_with_parser" and not self.html_content:
            # Store the URL and parser config for later use
            self.pending_parse_url = function_args.get("url", self.url)
            self.parser_config = function_args.get("parser_config", {})
            
            # Add a message to the chat
            self.chat_widget.chat_display.append('<div style="color: #666666; font-style: italic;">Need to fetch HTML before parsing...</div>')
        
        # Execute the function
        function_response = self.function_manager.execute_function(function_name, function_args)
        
        # Add the function response to the chat history
        self.chat_widget.history.add_message(ChatMessage(
            ChatMessage.ROLE_SYSTEM,
            f"Function {function_name} returned: {json.dumps(function_response)}"
        ))
        
        # If the function is fetching a webpage, we'll get the response asynchronously
        # so we don't need to call the LLM again right now
        if function_name == "fetch_webpage":
            return
        
        # Call the LLM again with the function response
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
        
        if not self.parser:
            # Create a new parser
            self.parser = URLParser(
                name=name,
                url_pattern=url_pattern,
                parser=json.dumps(parser_data),
                meta_data=meta_data,
                chat_data={"chat_history": self.chat_widget.history.to_dict()}
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
            self.parser.chat_data = {"chat_history": self.chat_widget.history.to_dict()}
            
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