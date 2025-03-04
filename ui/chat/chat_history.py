#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - Chat History

This module provides the ChatHistory class for managing chat message history.
"""

from typing import List, Dict, Any
from .chat_message import ChatMessage


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