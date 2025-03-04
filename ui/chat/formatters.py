#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - Chat Formatters

This module provides text formatting utilities for the chat display.
"""

import re
import html


def format_content(content: str) -> str:
    """Format content with Markdown-like processing."""
    # Escape HTML content first to prevent rendering issues
    escaped_content = html.escape(content)
    
    # Handle code blocks (after escaping HTML)
    escaped_content = format_code_blocks(escaped_content)
    
    # Handle inline code (after code blocks)
    escaped_content = format_inline_code(escaped_content)
    
    # Handle links (after escaping HTML)
    escaped_content = format_links(escaped_content)
    
    # Format paragraphs
    paragraphs = escaped_content.split('\n\n')
    formatted_content = ''.join([f'<p>{p.replace(chr(10), "<br>")}</p>' for p in paragraphs])
    
    return formatted_content


def format_inline_code(text: str) -> str:
    """Format inline code in the text."""
    # Pattern for inline code (single backticks)
    pattern = r'`([^`]+)`'
    
    # Replace inline code with styled spans
    return re.sub(
        pattern, 
        lambda m: f'<code style="background-color: #f5f5f5; padding: 2px 4px; border-radius: 3px; font-family: monospace;">{m.group(1)}</code>', 
        text
    )


def format_code_blocks(text: str) -> str:
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


def format_links(text: str) -> str:
    """Format links in the text."""
    # Simple link formatting (can be enhanced)
    
    # URL pattern
    url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+\.[^\s<>"]+(?=[^\s<>"])'
    
    # Replace URLs with HTML links
    return re.sub(url_pattern, lambda m: f'<a href="{m.group(0)}" style="color: #4a86e8;">{m.group(0)}</a>', text) 