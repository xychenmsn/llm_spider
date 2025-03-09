#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - Chat Widget

This module provides the ChatWidget class for displaying and interacting with the chat.
"""

from datetime import datetime
import os

from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtCore import Qt, Signal

from .chat_message import ChatMessage
from .chat_history import ChatHistory
from .formatters import format_content, format_inline_code, format_code_blocks, format_links


class ChatWidget(QtWidgets.QWidget):
    """Widget for displaying and interacting with the chat."""
    
    message_sent = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.history = ChatHistory()
        self.is_processing = False
        self.current_streaming_message = ""
        self.is_streaming = False
        self.log_file = None
        self.setup_ui()
        self._setup_logging()
        
    def _setup_logging(self):
        """Set up logging for the chat content."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = "tmp/parser_designer_log"
        os.makedirs(log_dir, exist_ok=True)
        self.log_file = os.path.join(log_dir, f"chat_{timestamp}.txt")
    
    def _log_content(self, content: str):
        """Log content to the log file."""
        if self.log_file:
            try:
                timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S] ")
                with open(self.log_file, 'a') as f:
                    f.write(f"{timestamp}{content}\n")
            except Exception:
                # Silently fail if we can't write to the log file
                pass
    
    def _get_chat_content(self) -> str:
        """Get the current chat content in a format suitable for logging."""
        try:
            content = self.chat_display.toPlainText()
            # Add horizontal line between messages for better readability
            content = content.replace("\n(", "\n" + "-"*80 + "\n(")
            return content
        except Exception:
            return "=== Chat content unavailable ==="
    
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
        formatted_content = format_content(self.current_streaming_message)
        
        # Clear the display and re-add everything
        cursor = self.chat_display.textCursor()
        cursor.select(QtGui.QTextCursor.Document)
        cursor.removeSelectedText()
        
        # Re-add all messages from history except the current streaming one
        for message in self.history.messages:
            if message.role == ChatMessage.ROLE_SYSTEM:
                # Display system messages with a different style
                timestamp = message.timestamp.strftime("%H:%M:%S")
                self.chat_display.append(f'<div style="color: #666666; font-style: italic; margin-top: 5px;">{message.content} <span style="color: #999999; font-size: 0.8em;">({timestamp})</span></div>')
            elif message.role != ChatMessage.ROLE_SYSTEM:  # Skip system messages
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
        return format_content(content)
    
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
        formatted_content = format_content(message.content)
        
        # Add the message to the display
        self.chat_display.append(f"{header}<div style='margin-left: 10px;'>{formatted_content}</div>")
        
        # Scroll to bottom
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )
    
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
        formatted_content = format_content(content)
        
        # Clear the display and re-add everything
        cursor = self.chat_display.textCursor()
        cursor.select(QtGui.QTextCursor.Document)
        cursor.removeSelectedText()
        
        # Re-add all messages from history
        for message in self.history.messages:
            if message.role == ChatMessage.ROLE_SYSTEM:
                # Display system messages with a different style
                timestamp = message.timestamp.strftime("%H:%M:%S")
                self.chat_display.append(f'<div style="color: #666666; font-style: italic; margin-top: 5px;">{message.content} <span style="color: #999999; font-size: 0.8em;">({timestamp})</span></div>')
            elif message.role != ChatMessage.ROLE_SYSTEM:
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
    
    def __del__(self):
        """Clean up when the widget is destroyed."""
        # No longer need to log here as it's handled in the ParserDesignerWindow
        pass 