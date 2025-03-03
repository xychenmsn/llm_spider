#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - Chat Components

This module provides chat-related UI components for the LLM Spider application.
"""

import json
import re
import html
from typing import List, Dict, Optional, Any
from datetime import datetime

from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtCore import Qt, Signal


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
        self.is_processing = False
        self.current_streaming_message = ""
        self.is_streaming = False
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
        """Receive a complete message from the assistant."""
        # If we were streaming, clear the streaming state
        self.is_streaming = False
        self.current_streaming_message = ""
        
        # Remove the typing indicator if it exists
        self._remove_typing_indicator()
        
        # Add assistant message to history
        assistant_message = ChatMessage(ChatMessage.ROLE_ASSISTANT, content)
        self.history.add_message(assistant_message)
        
        # Display assistant message
        self.display_message(assistant_message)
    
    def receive_chunk(self, content: str):
        """Receive a chunk of a message from the assistant."""
        # If this is the first chunk, prepare the display
        if not self.is_streaming:
            self.is_streaming = True
            self.current_streaming_message = ""
            self._remove_typing_indicator()
            
            # Start a new assistant message with a unique ID
            timestamp = datetime.now().strftime("%H:%M:%S")
            sender = "Assistant"
            color = "#6aa84f"  # Green
            
            # Format header
            header = f'<div style="margin-top: 10px;"><span style="color: {color}; font-weight: bold;">{sender}</span> <span style="color: #999999; font-size: 0.8em;">({timestamp})</span></div>'
            
            # Add the message header to the display
            self.chat_display.append(header)
            
            # Add a placeholder for the streaming content
            self.chat_display.append('<div id="streaming-content" style="margin-left: 10px;"></div>')
        
        # Accumulate the content
        self.current_streaming_message += content
        
        # Format the accumulated content with Markdown-like processing
        formatted_content = self._format_content(self.current_streaming_message)
        
        # Clear the display and re-add everything
        cursor = self.chat_display.textCursor()
        cursor.select(QtGui.QTextCursor.Document)
        cursor.removeSelectedText()
        
        # Re-add all messages from history except the current streaming one
        for message in self.history.messages:
            if message.role != ChatMessage.ROLE_SYSTEM:  # Skip system messages
                self.display_message(message)
        
        # Add the streaming message header
        timestamp = datetime.now().strftime("%H:%M:%S")
        header = f'<div style="margin-top: 10px;"><span style="color: #6aa84f; font-weight: bold;">Assistant</span> <span style="color: #999999; font-size: 0.8em;">({timestamp})</span></div>'
        self.chat_display.append(header)
        
        # Add the current streaming content
        self.chat_display.append(f'<div style="margin-left: 10px;">{formatted_content}</div>')
        
        # Force update to ensure the chunk is displayed immediately
        self.chat_display.repaint()
        
        # Scroll to bottom
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )
        
        # Process Qt events to ensure UI updates
        QtWidgets.QApplication.processEvents()
    
    def _format_content(self, content: str):
        """Format content with Markdown-like processing."""
        # Escape HTML content first to prevent rendering issues
        escaped_content = html.escape(content)
        
        # Handle code blocks (after escaping HTML)
        escaped_content = self._format_code_blocks(escaped_content)
        
        # Handle inline code (after code blocks)
        escaped_content = self._format_inline_code(escaped_content)
        
        # Handle links (after escaping HTML)
        escaped_content = self._format_links(escaped_content)
        
        # Format paragraphs
        paragraphs = escaped_content.split('\n\n')
        formatted_content = ''.join([f'<p>{p.replace(chr(10), "<br>")}</p>' for p in paragraphs])
        
        return formatted_content
    
    def _format_inline_code(self, text: str) -> str:
        """Format inline code in the text."""
        # Pattern for inline code (single backticks)
        pattern = r'`([^`]+)`'
        
        # Replace inline code with styled spans
        return re.sub(
            pattern, 
            lambda m: f'<code style="background-color: #f5f5f5; padding: 2px 4px; border-radius: 3px; font-family: monospace;">{m.group(1)}</code>', 
            text
        )
    
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
        
        # Format content with our _format_content method
        formatted_content = self._format_content(message.content)
        
        # Add the message to the display
        self.chat_display.append(f"{header}<div style='margin-left: 10px;'>{formatted_content}</div>")
        
        # Scroll to bottom
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )
    
    def _format_code_blocks(self, text: str) -> str:
        """Format code blocks in the text."""
        # Use a more robust approach to handle code blocks
        pattern = r'```(\w*)\n(.*?)```'
        
        # Function to process each code block match
        def replace_code_block(match):
            language = match.group(1)
            code_content = match.group(2)
            return f'<pre style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; font-family: monospace;">{code_content}</pre>'
        
        # Replace code blocks with formatted HTML
        result = re.sub(pattern, replace_code_block, text, flags=re.DOTALL)
        return result
    
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
    
    def set_processing(self, is_processing: bool):
        """Enable or disable input during processing."""
        self.is_processing = is_processing
        self.text_input.setReadOnly(is_processing)
        self.send_button.setDisabled(is_processing)
        self.upload_button.setDisabled(is_processing)
        
        if is_processing:
            self.text_input.setPlaceholderText("Waiting for AI response...")
        else:
            self.text_input.setPlaceholderText("Type your message here...")
    
    def _remove_typing_indicator(self):
        """Remove the typing indicator from the chat display."""
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.select(QtGui.QTextCursor.LineUnderCursor)
        cursor.removeSelectedText()
        cursor.deletePreviousChar()  # Remove the newline 
    
    def finalize_streaming_message(self, final_content=None):
        """Finalize the streaming message with the complete content."""
        if not self.is_streaming:
            return
            
        # Use the provided final content or the current accumulated content
        content = final_content or self.current_streaming_message
        
        # Format the content
        formatted_content = self._format_content(content)
        
        # Clear the display and re-add everything
        cursor = self.chat_display.textCursor()
        cursor.select(QtGui.QTextCursor.Document)
        cursor.removeSelectedText()
        
        # Re-add all messages from history
        for message in self.history.messages:
            if message.role != ChatMessage.ROLE_SYSTEM:  # Skip system messages
                self.display_message(message)
        
        # Add the final message
        timestamp = datetime.now().strftime("%H:%M:%S")
        header = f'<div style="margin-top: 10px;"><span style="color: #6aa84f; font-weight: bold;">Assistant</span> <span style="color: #999999; font-size: 0.8em;">({timestamp})</span></div>'
        self.chat_display.append(header)
        self.chat_display.append(f'<div style="margin-left: 10px;">{formatted_content}</div>')
        
        # Reset streaming state
        self.is_streaming = False
        self.current_streaming_message = ""
        
        # Force update and scroll
        self.chat_display.repaint()
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        ) 