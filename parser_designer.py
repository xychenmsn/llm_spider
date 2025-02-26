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
from typing import List, Dict, Optional, Any
from datetime import datetime

from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QPixmap, QImage
from dotenv import load_dotenv

import openai
from db.models import URLParser
from db.db_client import db_client

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

# Configure OpenAI
api_key = os.getenv("OPENAI_API_KEY")
if not api_key or api_key == "your_openai_api_key_here":
    logger.warning("OpenAI API key not found or not set. Chat functionality will not work.")

openai_client = openai.OpenAI(api_key=api_key)


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
    
    def __init__(self, parent=None, parser_id=None):
        super().__init__(parent)
        self.parser_id = parser_id
        self.parser = None
        self.chat_history = ChatHistory()
        
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
        
        # Header with parser name
        header_layout = QtWidgets.QHBoxLayout()
        
        self.name_label = QtWidgets.QLabel("New Parser")
        font = self.name_label.font()
        font.setPointSize(16)
        font.setBold(True)
        self.name_label.setFont(font)
        header_layout.addWidget(self.name_label)
        
        header_layout.addStretch()
        
        # Save button
        self.save_button = QtWidgets.QPushButton("Save Parser")
        self.save_button.clicked.connect(self.save_parser)
        header_layout.addWidget(self.save_button)
        
        layout.addLayout(header_layout)
        
        # Toolbar with buttons
        toolbar_layout = QtWidgets.QHBoxLayout()
        
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
            self.name_label.setText(self.parser.name)
            
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
            "You can suggest regex patterns, parsing strategies, and help with implementation details. "
            "Be specific and provide code examples when appropriate."
        )
        
        if self.parser:
            # Add parser-specific context
            system_prompt += f"\n\nYou are currently editing the parser named '{self.parser.name}' "
            system_prompt += f"with URL pattern: {self.parser.url_pattern}"
        
        self.chat_widget.set_system_prompt(system_prompt)
        
        # If no existing chat history, send a welcome message
        if not self.chat_history.messages or all(msg.role == ChatMessage.ROLE_SYSTEM for msg in self.chat_history.messages):
            welcome_message = (
                "Welcome to the Parser Designer! I'm here to help you create a URL parser. "
                "Let's start by discussing what kind of URLs you want to parse and what information you want to extract. "
                "You can ask me questions, request code examples, or get suggestions for regex patterns."
            )
            self.chat_widget.receive_message(welcome_message)
    
    def on_message_sent(self, message: str):
        """Handle a message sent by the user."""
        # Call OpenAI API to get a response
        self._get_ai_response()
    
    def _get_ai_response(self):
        """Get a response from the OpenAI API."""
        try:
            # Show a loading indicator
            self.chat_widget.chat_display.append('<div style="color: #999999; font-style: italic;">Assistant is typing...</div>')
            
            # Prepare messages for API call
            messages = self.chat_widget.history.get_openai_messages()
            
            # Call OpenAI API
            response = openai_client.chat.completions.create(
                model="gpt-4",  # Use an appropriate model
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            # Extract response text
            response_text = response.choices[0].message.content
            
            # Remove the "typing" indicator
            cursor = self.chat_widget.chat_display.textCursor()
            cursor.movePosition(QtGui.QTextCursor.End)
            cursor.select(QtGui.QTextCursor.LineUnderCursor)
            cursor.removeSelectedText()
            cursor.deletePreviousChar()  # Remove the newline
            
            # Display the response
            self.chat_widget.receive_message(response_text)
            
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            self.chat_widget.receive_message(f"Sorry, I encountered an error: {str(e)}")
    
    def open_browser(self):
        """Open a browser for testing the parser."""
        # This will be implemented later
        QtWidgets.QMessageBox.information(
            self, "Not Implemented", "Browser functionality will be implemented later."
        )
    
    def save_parser(self):
        """Save the parser with the chat history."""
        if not self.parser:
            # If creating a new parser, open a dialog to get the name and URL pattern
            dialog = NewParserDialog(self)
            if dialog.exec():
                name = dialog.name_input.text().strip()
                url_pattern = dialog.pattern_input.text().strip()
                parser_type = dialog.parser_input.text().strip() or "custom_parser"
                
                if not name or not url_pattern:
                    QtWidgets.QMessageBox.warning(
                        self, "Missing Information", "Please provide a name and URL pattern."
                    )
                    return
                
                # Create a new parser
                self.parser = URLParser(
                    name=name,
                    url_pattern=url_pattern,
                    parser=parser_type,
                    meta_data={},
                    chat_data={"chat_history": self.chat_widget.history.to_dict()}
                )
                
                try:
                    created_parser = db_client.create(self.parser)
                    if created_parser:
                        self.parser = created_parser
                        self.name_label.setText(self.parser.name)
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
            try:
                # Update chat history
                if isinstance(self.parser.chat_data, str):
                    chat_data = json.loads(self.parser.chat_data)
                else:
                    chat_data = self.parser.chat_data or {}
                
                chat_data["chat_history"] = self.chat_widget.history.to_dict()
                
                # Update parser
                updated_parser = db_client.update(
                    URLParser,
                    self.parser.id,
                    chat_data=chat_data
                )
                
                if updated_parser:
                    QtWidgets.QMessageBox.information(
                        self, "Success", f"Parser '{self.parser.name}' updated successfully."
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