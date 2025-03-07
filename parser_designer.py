#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - Parser Designer Interface

This module provides a UI for designing URL parsers with LLM assistance.
"""

# Import from refactored modules
from ui.parser_designer import ParserDesignerWindow, NewParserDialog
from ui.chat import ChatMessage, ChatHistory, ChatWidget
from llm.worker import LLMWorker
from llm.functions import FUNCTION_SCHEMAS, FunctionExecutor
from scraping.utils import fetch_webpage_html, parse_list_page, parse_content_page

# This file is kept for backward compatibility
# All functionality has been moved to the respective modules 