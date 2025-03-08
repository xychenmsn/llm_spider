#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Example script demonstrating the use of the LLMWrapper class.
"""

import os
import sys
import logging
from typing import Dict, Any
from dotenv import load_dotenv

# Add the parent directory to the path so we can import the llm module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm.llm_client import LLMClient
from llm.llm_wrapper import LLMWrapper
from llm.function import Function

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Define a custom function for the example
class SearchPythonDocs(Function):
    """Function to search Python documentation."""
    
    name = "search_python_docs"
    description = "Search the Python documentation for information"
    parameters = {
        "query": {
            "type": "string",
            "description": "The search query"
        }
    }
    required_parameters = {"query"}
    
    def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the function with the given arguments."""
        query = args.get("query", "")
        if not query:
            return {"error": "Query is required"}
        
        # In a real implementation, this would search the Python docs
        # For this example, we'll just return a mock response
        return {
            "results": [
                {
                    "title": f"Python documentation for: {query}",
                    "url": f"https://docs.python.org/3/search.html?q={query}",
                    "summary": f"This is a mock result for the query: {query}"
                }
            ]
        }

def main():
    """Run the example."""
    # Define a system prompt
    system_prompt = """
    You are a helpful AI assistant specialized in answering questions about Python programming.
    Your primary goal is to provide accurate, concise, and helpful information about Python.
    If asked about topics unrelated to Python programming, politely redirect the conversation
    back to Python-related topics.
    """
    
    # Create the LLM wrapper with focus mode enabled by default
    wrapper = LLMWrapper(
        system_prompt=system_prompt,
        max_history_tokens=2000,
        model="gpt-4-turbo-preview",
        focus_mode=True,  # Enable focus mode by default
        enable_functions=True  # Enable function calling
    )
    
    print("\n=== LLM Wrapper Example ===")
    print("This example demonstrates the LLMWrapper class.")
    print("Type 'exit' to quit, 'clear' to clear history, 'focus on' to enable focus mode, 'focus off' to disable it.\n")
    
    focus_mode = wrapper.focus_mode  # Get the initial focus mode setting
    
    while True:
        # Get user input
        user_input = input("\nYou: ")
        
        # Check for special commands
        if user_input.lower() == 'exit':
            print("Exiting...")
            break
        elif user_input.lower() == 'clear':
            wrapper.clear_history()
            print("Chat history cleared.")
            continue
        elif user_input.lower() == 'focus on':
            focus_mode = True
            print("Focus mode enabled. The assistant will only respond to Python-related queries.")
            continue
        elif user_input.lower() == 'focus off':
            focus_mode = False
            print("Focus mode disabled. The assistant will respond to all queries.")
            continue
        
        # Call the LLM
        print("\nAssistant: ", end="", flush=True)
        
        try:
            # Use streaming for a more interactive experience
            response_stream = wrapper.chat(
                user_input=user_input,
                focus_mode=focus_mode,  # Override the default focus mode if needed
                stream=True,
                enable_functions=True  # Enable function calling for this request
            )
            
            # Process the stream
            final_response = None
            for chunk in response_stream:
                if isinstance(chunk, str):
                    print(chunk, end="", flush=True)
                else:
                    final_response = chunk
            
            print()  # Add a newline after the response
            
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main() 