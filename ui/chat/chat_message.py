#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - Chat Message

This module provides the ChatMessage class for representing messages in the chat.
"""

from typing import Dict, Optional, Any
from datetime import datetime


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