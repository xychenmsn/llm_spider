#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the LLMWrapper class.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import json

# Add the parent directory to the path so we can import the llm module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm.llm_client import LLMClient, LLMResponse
from llm.llm_wrapper import LLMWrapper
from llm.function import Function
from llm.function_manager import FunctionManager

class TestLLMWrapper(unittest.TestCase):
    """Test cases for the LLMWrapper class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.system_prompt = "You are a test assistant."
        self.mock_client = MagicMock(spec=LLMClient)
        self.custom_function_schemas = [
            {
                "type": "function",
                "function": {
                    "name": "test_function",
                    "description": "A test function",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "test_param": {
                                "type": "string",
                                "description": "A test parameter"
                            }
                        },
                        "required": ["test_param"]
                    }
                }
            }
        ]
        self.wrapper = LLMWrapper(
            system_prompt=self.system_prompt,
            llm_client=self.mock_client,
            max_history_tokens=1000,
            model="test-model",
            focus_mode=True,
            enable_functions=True,
            custom_function_schemas=self.custom_function_schemas
        )
    
    def test_init(self):
        """Test initialization of the wrapper."""
        self.assertEqual(self.wrapper.system_prompt, self.system_prompt)
        self.assertEqual(self.wrapper.model, "test-model")
        self.assertEqual(self.wrapper.max_history_tokens, 1000)
        self.assertEqual(self.wrapper.history, [])
        self.assertTrue(self.wrapper.focus_mode)
        self.assertTrue(self.wrapper.enable_functions)
        self.assertEqual(self.wrapper.custom_function_schemas, self.custom_function_schemas)
    
    def test_estimate_tokens(self):
        """Test token estimation."""
        # Test with empty string
        self.assertEqual(self.wrapper._estimate_tokens(""), 4)  # Just the message overhead
        
        # Test with a string
        text = "This is a test."
        expected = int(len(text) * 0.25) + 4
        self.assertEqual(self.wrapper._estimate_tokens(text), expected)
    
    def test_prepare_messages_no_history(self):
        """Test message preparation with no history."""
        user_input = "Hello, world!"
        messages = self.wrapper._prepare_messages(user_input)
        
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[0]["content"], self.system_prompt)
        self.assertEqual(messages[1]["role"], "user")
        self.assertEqual(messages[1]["content"], user_input)
    
    def test_prepare_messages_with_history(self):
        """Test message preparation with history."""
        # Add some history
        self.wrapper.history = [
            {"role": "user", "content": "First message"},
            {"role": "assistant", "content": "First response"},
            {"role": "user", "content": "Second message"},
            {"role": "assistant", "content": "Second response"}
        ]
        
        user_input = "Third message"
        messages = self.wrapper._prepare_messages(user_input)
        
        # Should include system prompt, all history, and current user input
        self.assertEqual(len(messages), 6)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["content"], "First message")
        self.assertEqual(messages[5]["content"], "Third message")
    
    def test_prepare_messages_focus_mode(self):
        """Test message preparation with focus mode enabled."""
        user_input = "Test input"
        messages = self.wrapper._prepare_messages(user_input, focus_mode=True)
        
        # Check that the user input is wrapped in JSON
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")
        
        # Parse the JSON to verify structure
        wrapped_input = json.loads(messages[1]["content"])
        self.assertEqual(wrapped_input["user_input"], user_input)
        self.assertIn("instructions", wrapped_input)
    
    @patch('llm.llm_client.LLMClient.call_llm')
    def test_chat_non_streaming(self, mock_call_llm):
        """Test chat method with non-streaming response."""
        # Set up the mock
        mock_response = LLMResponse(content="Test response")
        mock_call_llm.return_value = mock_response
        
        # Call the method
        response = self.wrapper.chat("Test input", stream=False)
        
        # Verify the response
        self.assertEqual(response, mock_response)
        
        # Verify history was updated
        self.assertEqual(len(self.wrapper.history), 2)
        self.assertEqual(self.wrapper.history[0]["role"], "user")
        self.assertEqual(self.wrapper.history[0]["content"], "Test input")
        self.assertEqual(self.wrapper.history[1]["role"], "assistant")
        self.assertEqual(self.wrapper.history[1]["content"], "Test response")
    
    def test_clear_history(self):
        """Test clearing history."""
        # Add some history
        self.wrapper.history = [
            {"role": "user", "content": "Test"},
            {"role": "assistant", "content": "Response"}
        ]
        
        # Clear history
        self.wrapper.clear_history()
        
        # Verify history is empty
        self.assertEqual(self.wrapper.history, [])
    
    def test_get_history(self):
        """Test getting history."""
        # Add some history
        history = [
            {"role": "user", "content": "Test"},
            {"role": "assistant", "content": "Response"}
        ]
        self.wrapper.history = history.copy()
        
        # Get history
        result = self.wrapper.get_history()
        
        # Verify it's a copy, not the original
        self.assertEqual(result, history)
        self.assertIsNot(result, self.wrapper.history)

    @patch('llm.llm_client.LLMClient.call_llm')
    @patch('llm.functions.get_function_schemas')
    def test_chat_with_constructor_settings(self, mock_get_schemas, mock_call_llm):
        """Test chat method using constructor settings."""
        # Set up the mocks
        mock_response = LLMResponse(content="Test response")
        mock_call_llm.return_value = mock_response
        mock_get_schemas.return_value = [{"type": "function", "function": {"name": "registered_function"}}]
        
        # Call the method without overriding focus_mode or enable_functions
        response = self.wrapper.chat("Test input", stream=False)
        
        # Verify the call used the constructor settings
        mock_call_llm.assert_called_once()
        call_args = mock_call_llm.call_args[1]
        self.assertEqual(call_args["model"], "test-model")
        self.assertEqual(call_args["function_schemas"], self.custom_function_schemas)
        
        # Verify the messages were prepared with focus mode
        messages = call_args["messages"]
        user_message = messages[-1]
        self.assertEqual(user_message["role"], "user")
        # Check that the content is JSON (focus mode)
        try:
            wrapped_input = json.loads(user_message["content"])
            self.assertEqual(wrapped_input["user_input"], "Test input")
        except json.JSONDecodeError:
            self.fail("User message content is not valid JSON (focus mode not applied)")

    @patch('llm.llm_client.LLMClient.call_llm')
    @patch('llm.functions.get_function_schemas')
    def test_chat_override_constructor_settings(self, mock_get_schemas, mock_call_llm):
        """Test chat method overriding constructor settings."""
        # Set up the mocks
        mock_response = LLMResponse(content="Test response")
        mock_call_llm.return_value = mock_response
        registered_schemas = [{"type": "function", "function": {"name": "registered_function"}}]
        mock_get_schemas.return_value = registered_schemas
        
        # Override function schemas
        new_schemas = [{"type": "function", "function": {"name": "new_function"}}]
        
        # Call the method with overridden focus_mode and custom_function_schemas
        response = self.wrapper.chat(
            "Test input", 
            focus_mode=False,  # Override constructor setting
            enable_functions=True,  # Keep functions enabled
            custom_function_schemas=new_schemas,  # Override constructor setting
            stream=False
        )
        
        # Verify the call used the overridden settings
        mock_call_llm.assert_called_once()
        call_args = mock_call_llm.call_args[1]
        self.assertEqual(call_args["function_schemas"], new_schemas)
        
        # Verify the messages were prepared without focus mode
        messages = call_args["messages"]
        user_message = messages[-1]
        self.assertEqual(user_message["role"], "user")
        self.assertEqual(user_message["content"], "Test input")  # Not JSON wrapped
        
    @patch('llm.llm_client.LLMClient.call_llm')
    @patch('llm.functions.get_function_schemas')
    def test_chat_with_registered_functions(self, mock_get_schemas, mock_call_llm):
        """Test chat method using registered functions instead of custom schemas."""
        # Set up the mocks
        mock_response = LLMResponse(content="Test response")
        mock_call_llm.return_value = mock_response
        registered_schemas = [{"type": "function", "function": {"name": "registered_function"}}]
        mock_get_schemas.return_value = registered_schemas
        
        # Create a wrapper without custom schemas
        wrapper = LLMWrapper(
            system_prompt=self.system_prompt,
            llm_client=self.mock_client,
            model="test-model",
            enable_functions=True,
            custom_function_schemas=None  # No custom schemas
        )
        
        # Call the chat method
        response = wrapper.chat("Test input", stream=False)
        
        # Verify registered schemas were used
        mock_call_llm.assert_called_once()
        call_args = mock_call_llm.call_args[1]
        self.assertEqual(call_args["function_schemas"], registered_schemas)
        mock_get_schemas.assert_called_once()

if __name__ == "__main__":
    unittest.main() 