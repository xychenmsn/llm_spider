#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - Chat Components

This module provides chat-related UI components for the LLM Spider application.
"""

import json
import re
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
    
    def receive_chunk(self, content: str):
        """Receive a chunk of a message from the assistant."""
        # Append the chunk to the last message in the chat display
        self.chat_display.moveCursor(QtGui.QTextCursor.End)
        self.chat_display.insertPlainText(content)
        
        # Scroll to bottom
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
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