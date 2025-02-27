#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - Parser Designer Interface

This module provides a UI for designing URL parsers with LLM assistance.
"""

import os
import sys
import json
import logging
import re
import base64
from typing import List, Dict, Optional, Any, Union
from datetime import datetime

from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QPixmap, QImage
from dotenv import load_dotenv

import openai
from db.models import URLParser
from db.db_client import db_client

# For web scraping
import requests
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

# Configure OpenAI
api_key = os.getenv("OPENAI_API_KEY")
if not api_key or api_key == "your_openai_api_key_here":
    logger.warning("OpenAI API key not found or not set. Chat functionality will not work.")
    print("Error: OPENAI_API_KEY not found or not properly set in environment variables.")
    openai_client = None
else:
    print(f"Using API key: {api_key[:8]}...{api_key[-4:] if api_key and len(api_key) > 12 else ''}")

    # Initialize the OpenAI client
    try:
        print("Initializing OpenAI client...")
        openai_client = openai.OpenAI(api_key=api_key)
        
        # Test the client with a simple request to verify it works
        # We'll only do this when the module is run directly, not when imported
        if __name__ == "__main__":
            print("Testing OpenAI API connection...")
            test_response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": "Test connection"}],
                max_tokens=5
            )
            print(f"OpenAI API connection successful! Response: {test_response.choices[0].message.content}")
        
        logger.info("OpenAI API connection successful")
    except Exception as e:
        logger.error(f"Error initializing OpenAI client: {str(e)}")
        print(f"Error initializing OpenAI client: {str(e)}")
        # Create a dummy client that will be replaced with proper error handling
        openai_client = None

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

# Helper functions for web scraping
def fetch_webpage_html(url: str) -> str:
    """Fetch the HTML content of a webpage using requests."""
    try:
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        response.raise_for_status()
        return response.text
    except Exception as e:
        logger.error(f"Error fetching HTML: {str(e)}")
        return f"Error fetching HTML: {str(e)}"

def take_webpage_screenshot(url: str, timeout: int = 15000) -> Optional[str]:
    """Take a screenshot of a webpage using Playwright and return as base64."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            
            # Set a shorter timeout
            page.goto(url, timeout=timeout)
            
            # Wait for the page to load, but with a timeout
            try:
                page.wait_for_load_state("networkidle", timeout=timeout)
            except Exception as e:
                logger.warning(f"Timeout waiting for page to load: {str(e)}")
                # Continue anyway, we'll take a screenshot of what we have
            
            # Take a screenshot of the full page
            screenshot_bytes = page.screenshot(full_page=True, type='jpeg', quality=50)
            browser.close()
            
            # Convert to base64
            return base64.b64encode(screenshot_bytes).decode('utf-8')
    except Exception as e:
        logger.error(f"Error taking screenshot: {str(e)}")
        return None

def parse_list_page(html: str, selector: str, attribute: str) -> List[str]:
    """Parse a list page to extract URLs."""
    try:
        if not selector:
            return ["Error: No selector provided"]
            
        soup = BeautifulSoup(html, 'html.parser')
        elements = soup.select(selector)
        urls = []
        
        for element in elements:
            if attribute == 'href' and element.name == 'a':
                url = element.get('href')
                if url:
                    urls.append(url)
            elif attribute == 'text':
                urls.append(element.text.strip())
            else:
                attr_value = element.get(attribute)
                if attr_value:
                    urls.append(attr_value)
        
        return urls
    except Exception as e:
        logger.error(f"Error parsing list page: {str(e)}")
        return [f"Error parsing list page: {str(e)}"]

def parse_content_page(html: str, title_selector: str, date_selector: str, body_selector: str) -> Dict[str, str]:
    """Parse a content page to extract title, date, and body."""
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        title = ""
        date = ""
        body = ""
        
        if title_selector:
            title_element = soup.select_one(title_selector)
            title = title_element.text.strip() if title_element else ""
        
        if date_selector:
            date_element = soup.select_one(date_selector)
            date = date_element.text.strip() if date_element else ""
        
        if body_selector:
            body_element = soup.select_one(body_selector)
            body = body_element.text.strip() if body_element else ""
        
        return {
            "title": title,
            "date": date,
            "body": body
        }
    except Exception as e:
        logger.error(f"Error parsing content page: {str(e)}")
        return {"title": "", "date": "", "body": f"Error: {str(e)}"}

class ChatMessage:
    """Represents a message in the chat."""
    
    ROLE_USER = "user"
    ROLE_ASSISTANT = "assistant"
    ROLE_SYSTEM = "system"
    
    def __init__(self, role: str, content: str, timestamp: Optional[datetime] = None):
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now()
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to a dictionary for OpenAI API."""
        return {
            "role": self.role,
            "content": self.content
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatMessage':
        """Create a ChatMessage from a dictionary."""
        return cls(
            role=data.get("role", cls.ROLE_USER),
            content=data.get("content", ""),
            timestamp=datetime.fromisoformat(data.get("timestamp")) if "timestamp" in data else None
        )


class ChatHistory:
    """Manages the chat history."""
    
    def __init__(self):
        self.messages: List[ChatMessage] = []
        
    def add_message(self, message: ChatMessage) -> None:
        """Add a message to the history."""
        self.messages.append(message)
    
    def get_openai_messages(self) -> List[Dict[str, str]]:
        """Get messages formatted for OpenAI API."""
        return [msg.to_dict() for msg in self.messages]
    
    def clear(self) -> None:
        """Clear the chat history."""
        self.messages.clear()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization."""
        return {
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in self.messages
            ]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatHistory':
        """Create a ChatHistory from a dictionary."""
        history = cls()
        for msg_data in data.get("messages", []):
            history.add_message(ChatMessage.from_dict(msg_data))
        return history


class ChatWidget(QtWidgets.QWidget):
    """Widget for displaying and interacting with the chat."""
    
    message_sent = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.history = ChatHistory()
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the UI components."""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Chat display area
        self.chat_display = QtWidgets.QTextBrowser()
        self.chat_display.setOpenExternalLinks(True)
        self.chat_display.setReadOnly(True)
        self.chat_display.setMinimumHeight(300)
        layout.addWidget(self.chat_display)
        
        # Input area
        input_layout = QtWidgets.QHBoxLayout()
        
        # Text input
        self.text_input = QtWidgets.QTextEdit()
        self.text_input.setPlaceholderText("Type your message here...")
        self.text_input.setMaximumHeight(100)
        input_layout.addWidget(self.text_input, 4)
        
        # Upload image button
        self.upload_button = QtWidgets.QPushButton("Upload Image")
        self.upload_button.clicked.connect(self.upload_image)
        input_layout.addWidget(self.upload_button, 1)
        
        # Send button
        self.send_button = QtWidgets.QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_button, 1)
        
        layout.addLayout(input_layout)
        
        # Set up key event for sending messages with Ctrl+Enter
        self.text_input.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """Handle key events for the text input."""
        if obj is self.text_input and event.type() == QtCore.QEvent.KeyPress:
            if event.key() == Qt.Key_Return and event.modifiers() == Qt.ControlModifier:
                self.send_message()
                return True
        return super().eventFilter(obj, event)
    
    def upload_image(self):
        """Upload an image to include in the message."""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select Image", "", "Images (*.png *.jpg *.jpeg *.gif)"
        )
        
        if file_path:
            # For now, just insert the file path into the text input
            # In a real implementation, you would handle image uploads to OpenAI
            self.text_input.insertPlainText(f"\n[Image: {file_path}]\n")
    
    def send_message(self):
        """Send the current message."""
        message_text = self.text_input.toPlainText().strip()
        if not message_text:
            return
            
        # Add user message to history
        user_message = ChatMessage(ChatMessage.ROLE_USER, message_text)
        self.history.add_message(user_message)
        
        # Display user message
        self.display_message(user_message)
        
        # Clear input
        self.text_input.clear()
        
        # Emit signal
        self.message_sent.emit(message_text)
    
    def receive_message(self, content: str):
        """Receive a message from the assistant."""
        # Add assistant message to history
        assistant_message = ChatMessage(ChatMessage.ROLE_ASSISTANT, content)
        self.history.add_message(assistant_message)
        
        # Display assistant message
        self.display_message(assistant_message)
    
    def display_message(self, message: ChatMessage):
        """Display a message in the chat display."""
        # Format timestamp
        timestamp = message.timestamp.strftime("%H:%M:%S")
        
        # Format sender
        if message.role == ChatMessage.ROLE_USER:
            sender = "You"
            color = "#4a86e8"  # Blue
        elif message.role == ChatMessage.ROLE_ASSISTANT:
            sender = "Assistant"
            color = "#6aa84f"  # Green
        else:
            sender = "System"
            color = "#999999"  # Gray
        
        # Format header
        header = f'<div style="margin-top: 10px;"><span style="color: {color}; font-weight: bold;">{sender}</span> <span style="color: #999999; font-size: 0.8em;">({timestamp})</span></div>'
        
        # Format content with Markdown-like processing
        content = message.content
        
        # Handle code blocks
        content = self._format_code_blocks(content)
        
        # Handle links
        content = self._format_links(content)
        
        # Format paragraphs
        paragraphs = content.split('\n\n')
        formatted_content = ''.join([f'<p>{p.replace(chr(10), "<br>")}</p>' for p in paragraphs])
        
        # Add the message to the display
        self.chat_display.append(f"{header}<div style='margin-left: 10px;'>{formatted_content}</div>")
        
        # Scroll to bottom
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )
    
    def _format_code_blocks(self, text: str) -> str:
        """Format code blocks in the text."""
        # Simple code block formatting (can be enhanced)
        in_code_block = False
        lines = text.split('\n')
        formatted_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Check for code block markers
            if line.strip().startswith('```'):
                if not in_code_block:
                    # Start of code block
                    language = line.strip()[3:].strip()
                    formatted_lines.append(f'<pre style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; font-family: monospace;">')
                    in_code_block = True
                else:
                    # End of code block
                    formatted_lines.append('</pre>')
                    in_code_block = False
            elif in_code_block:
                # Inside code block
                formatted_lines.append(line.replace('<', '&lt;').replace('>', '&gt;'))
            else:
                # Regular text
                formatted_lines.append(line)
            
            i += 1
        
        # Close any open code block
        if in_code_block:
            formatted_lines.append('</pre>')
        
        return '\n'.join(formatted_lines)
    
    def _format_links(self, text: str) -> str:
        """Format links in the text."""
        # Simple link formatting (can be enhanced)
        import re
        
        # URL pattern
        url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+\.[^\s<>"]+(?=[^\s<>"])'
        
        # Replace URLs with HTML links
        return re.sub(url_pattern, lambda m: f'<a href="{m.group(0)}" style="color: #4a86e8;">{m.group(0)}</a>', text)
    
    def set_system_prompt(self, prompt: str):
        """Set the system prompt for the chat."""
        # Clear existing system messages
        self.history.messages = [msg for msg in self.history.messages if msg.role != ChatMessage.ROLE_SYSTEM]
        
        # Add new system message
        system_message = ChatMessage(ChatMessage.ROLE_SYSTEM, prompt)
        self.history.messages.insert(0, system_message)
    
    def clear_chat(self):
        """Clear the chat history and display."""
        self.history.clear()
        self.chat_display.clear()


class ParserDesignerWindow(QtWidgets.QDialog):
    """Dialog for designing URL parsers with LLM assistance."""
    
    def __init__(self, parent=None, parser_id=None, url=None):
        super().__init__(parent)
        self.parser_id = parser_id
        self.parser = None
        self.chat_history = ChatHistory()
        self.url = url
        
        # Parser data
        self.html_content = None
        self.screenshot_data = None
        self.parser_type = None  # 'list' or 'content'
        self.parser_config = {}
        self.parsed_results = None
        
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
        pass
    
    def _initialize_chat(self):
        """Initialize the chat with a system prompt."""
        system_prompt = (
            "You are an AI assistant helping to design a URL parser. "
            "Your goal is to help the user create a parser that can extract relevant information from URLs. "
            "You can suggest CSS selectors, parsing strategies, and help with implementation details. "
            "Be specific and provide code examples when appropriate. "
            "You have access to functions that can fetch webpage content, create parsers, and parse webpages."
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
            
            # Get AI response
            self._get_ai_response()
        elif not self.chat_history.messages or all(msg.role == ChatMessage.ROLE_SYSTEM for msg in self.chat_history.messages):
            # If no URL and no existing chat history, send a welcome message
            welcome_message = (
                "Welcome to the Parser Designer! I'm here to help you create a URL parser. "
                "Let's start by discussing what kind of URLs you want to parse and what information you want to extract. "
                "You can ask me questions, request code examples, or get suggestions for CSS selectors."
            )
            self.chat_widget.receive_message(welcome_message)
    
    def on_message_sent(self, message: str):
        """Handle a message sent by the user."""
        # Call OpenAI API to get a response
        self._get_ai_response()
    
    def _get_ai_response(self):
        """Get a response from the OpenAI API with function calling."""
        try:
            # Show a loading indicator
            self.chat_widget.chat_display.append('<div style="color: #999999; font-style: italic;">Assistant is typing...</div>')
            
            # Check if OpenAI client is properly initialized
            if openai_client is None:
                raise Exception("OpenAI client is not properly initialized. Please check your API key.")
            
            # Prepare messages for API call
            messages = self.chat_widget.history.get_openai_messages()
            
            # Call OpenAI API with function calling
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Use gpt-4o-mini as requested
                messages=messages,
                temperature=0.7,
                max_tokens=1000,
                tools=FUNCTION_SCHEMAS
            )
            
            # Extract response
            response_message = response.choices[0].message
            
            # Check if there's a function call
            if response_message.tool_calls:
                # Handle function calls
                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    # Add the assistant's function call to the chat history
                    self.chat_widget.history.add_message(ChatMessage(
                        ChatMessage.ROLE_ASSISTANT,
                        response_message.content or "I'll help you with that."
                    ))
                    
                    # Display the assistant's message
                    if response_message.content:
                        # Remove the "typing" indicator
                        self._remove_typing_indicator()
                        self.chat_widget.receive_message(response_message.content)
                    
                    # Execute the function
                    function_response = self._execute_function(function_name, function_args)
                    
                    # Add the function response to the chat history
                    self.chat_widget.history.add_message(ChatMessage(
                        ChatMessage.ROLE_SYSTEM,
                        f"Function {function_name} returned: {json.dumps(function_response)}"
                    ))
                    
                    # Call the API again with the function response
                    self._get_ai_response()
                    return
            
            # If no function call, just display the response
            response_text = response_message.content
            
            # Remove the "typing" indicator
            self._remove_typing_indicator()
            
            # Display the response
            self.chat_widget.receive_message(response_text)
            
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            
            # Remove the "typing" indicator
            self._remove_typing_indicator()
            
            # Display a more helpful error message
            error_message = str(e)
            if "authentication" in error_message.lower() or "api key" in error_message.lower():
                self.chat_widget.receive_message("Error: There seems to be an issue with your OpenAI API key. Please check that it's correctly set in your .env file.")
            else:
                self.chat_widget.receive_message(f"Sorry, I encountered an error: {error_message}")
    
    def _remove_typing_indicator(self):
        """Remove the typing indicator from the chat display."""
        cursor = self.chat_widget.chat_display.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.select(QtGui.QTextCursor.LineUnderCursor)
        cursor.removeSelectedText()
        cursor.deletePreviousChar()  # Remove the newline
    
    def _execute_function(self, function_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a function called by the LLM."""
        try:
            if function_name == "fetch_webpage":
                return self._fetch_webpage(args.get("url", ""))
            elif function_name == "create_list_parser":
                return self._create_list_parser(
                    args.get("selector", ""),
                    args.get("attribute", "href"),
                    args.get("description", "")
                )
            elif function_name == "create_content_parser":
                return self._create_content_parser(
                    args.get("title_selector", ""),
                    args.get("date_selector", ""),
                    args.get("body_selector", ""),
                    args.get("description", "")
                )
            elif function_name == "parse_with_parser":
                return self._parse_with_parser(
                    args.get("url", ""),
                    args.get("parser_type", "")
                )
            else:
                return {"error": f"Unknown function: {function_name}"}
        except Exception as e:
            logger.error(f"Error executing function {function_name}: {str(e)}")
            return {"error": str(e)}
    
    def _fetch_webpage(self, url: str) -> Dict[str, Any]:
        """Fetch the HTML content and screenshot of a webpage."""
        if not url:
            url = self.url
        
        if not url:
            return {"error": "No URL provided"}
        
        # Fetch HTML
        self.html_content = fetch_webpage_html(url)
        
        # Take screenshot
        self.screenshot_data = take_webpage_screenshot(url)
        
        # Display the screenshot in the chat
        if self.screenshot_data:
            # Create a QImage from the base64 data
            image_data = base64.b64decode(self.screenshot_data)
            image = QImage()
            image.loadFromData(image_data)
            
            # Scale the image to a reasonable size
            max_width = 600
            if image.width() > max_width:
                image = image.scaledToWidth(max_width, Qt.SmoothTransformation)
            
            # Convert to QPixmap and display
            pixmap = QPixmap.fromImage(image)
            
            # Add the image to the chat
            self.chat_widget.chat_display.append('<div style="text-align: center;">')
            self.chat_widget.chat_display.append('<p style="color: #666666; font-style: italic;">Screenshot:</p>')
            
            # Create a label for the image
            label = QtWidgets.QLabel()
            label.setPixmap(pixmap)
            label.setAlignment(Qt.AlignCenter)
            
            # Add the label to the chat display
            self.chat_widget.chat_display.insertHtml(f'<img src="data:image/jpeg;base64,{self.screenshot_data}" style="max-width: {max_width}px; max-height: 400px;" />')
            self.chat_widget.chat_display.append('</div>')
        
        # Return a summary of the HTML content
        html_preview = self.html_content[:1000] + "..." if len(self.html_content) > 1000 else self.html_content
        
        return {
            "url": url,
            "html_preview": html_preview,
            "has_screenshot": self.screenshot_data is not None,
            "html_length": len(self.html_content)
        }
    
    def _create_list_parser(self, selector: str, attribute: str, description: str) -> Dict[str, Any]:
        """Create a parser for a list page."""
        self.parser_type = "list"
        self.parser_config = {
            "selector": selector,
            "attribute": attribute,
            "description": description
        }
        
        # Update the name input if it's empty
        if not self.name_input.text():
            self.name_input.setText(f"List Parser - {self.url}")
        
        # Update the URL pattern if it's empty
        if not self.url_input.text():
            self.url_input.setText(self.url)
        
        return {
            "parser_type": "list",
            "config": self.parser_config,
            "message": "List parser created successfully"
        }
    
    def _create_content_parser(self, title_selector: str, date_selector: str, body_selector: str, description: str) -> Dict[str, Any]:
        """Create a parser for a content page."""
        self.parser_type = "content"
        self.parser_config = {
            "title_selector": title_selector,
            "date_selector": date_selector,
            "body_selector": body_selector,
            "description": description
        }
        
        # Update the name input if it's empty
        if not self.name_input.text():
            self.name_input.setText(f"Content Parser - {self.url}")
        
        # Update the URL pattern if it's empty
        if not self.url_input.text():
            self.url_input.setText(self.url)
        
        return {
            "parser_type": "content",
            "config": self.parser_config,
            "message": "Content parser created successfully"
        }
    
    def _parse_with_parser(self, url: str, parser_type: str) -> Dict[str, Any]:
        """Parse a webpage using the created parser."""
        try:
            if not url:
                url = self.url
            
            if not url:
                return {"error": "No URL provided"}
            
            if not self.html_content:
                self.html_content = fetch_webpage_html(url)
            
            if parser_type == "list" or self.parser_type == "list":
                # Parse as a list page
                if not self.parser_config:
                    return {"error": "No list parser configuration available"}
                
                selector = self.parser_config.get("selector", "")
                attribute = self.parser_config.get("attribute", "href")
                
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
            
            elif parser_type == "content" or self.parser_type == "content":
                # Parse as a content page
                if not self.parser_config:
                    return {"error": "No content parser configuration available"}
                
                title_selector = self.parser_config.get("title_selector", "")
                date_selector = self.parser_config.get("date_selector", "")
                body_selector = self.parser_config.get("body_selector", "")
                
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
            logger.error(f"Error parsing with parser: {str(e)}")
            self.chat_widget.chat_display.append(f'<div style="color: red; padding: 10px; border-radius: 5px; margin: 10px 0;">Error parsing with parser: {str(e)}</div>')
            return {"error": f"Error parsing with parser: {str(e)}"}
    
    def open_browser(self):
        """Open a browser for testing the parser."""
        # This will be implemented later
        QtWidgets.QMessageBox.information(
            self, "Not Implemented", "Browser functionality will be implemented later."
        )
    
    def save_parser(self):
        """Save the parser with the chat history."""
        name = self.name_input.text().strip()
        url_pattern = self.url_input.text().strip()
        
        if not name or not url_pattern:
            QtWidgets.QMessageBox.warning(
                self, "Missing Information", "Please provide a name and URL pattern."
            )
            return
        
        # Prepare parser data
        parser_data = {
            "type": self.parser_type,
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
            parser_type = self.parser_type or "custom_parser"
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
                else:
                    QtWidgets.QMessageBox.critical(
                        self, "Error", "Failed to update parser."
                    )
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self, "Error", f"Failed to update parser: {str(e)}"
                )


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