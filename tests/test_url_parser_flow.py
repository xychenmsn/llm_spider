#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for simulating the flow of using LLM wrapper for URL parsing.

This test simulates the following flow:
1. LLM asks user to input a URL
2. User inputs a URL
3. LLM calls a tool to retrieve HTML
4. LLM analyzes the HTML and identifies title, body, and date
5. LLM asks user to confirm if the extracted data looks good
6. If confirmed, LLM creates a parser
7. LLM shows the parser code and calls a tool to parse the HTML
8. LLM shows the parsing result
9. If parsing fails, LLM recreates the parser
10. If parsing succeeds, LLM asks user what else to do
11. Test also includes handling unrelated user messages

Usage:
    python tests/test_url_parser_flow.py

The test will first attempt to run with real LLM responses if the API keys are configured.
If that fails, it will fall back to using mocked responses.
"""

import os
import sys
import json
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from llm.llm_wrapper import LLMWrapper
from llm.function_manager import FunctionManager
from scraping.utils import fetch_webpage_html, parse_content_page

# Load environment variables
load_dotenv()

# Sample HTML content for testing
SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>文学城新闻频道 - 测试文章</title>
    <meta charset="utf-8">
</head>
<body>
    <div class="news-title">测试文章标题</div>
    <div class="news-date">2025-02-25 08:30</div>
    <div class="news-content">
        <p>这是一篇测试文章的内容。这是第一段。</p>
        <p>这是第二段内容。</p>
        <p>这是第三段内容。</p>
    </div>
</body>
</html>
"""

# Mock function to simulate fetching a webpage
def mock_fetch_webpage(url):
    """
    Mock function to simulate fetching a webpage.
    
    Args:
        url (str): The URL to fetch
        
    Returns:
        dict: A dictionary containing the HTML content and URL
    """
    return {
        "html": SAMPLE_HTML,
        "url": url
    }

# Mock function to simulate parsing with a parser
def mock_parse_with_parser(html, parser_name=None):
    """
    Mock function to simulate parsing with a parser.
    
    Args:
        html (str): The HTML content to parse
        parser_name (str, optional): The name of the parser to use
        
    Returns:
        dict: A dictionary containing the parsing result
    """
    # First attempt fails to simulate the need for parser improvement
    if parser_name == "first_attempt":
        return {
            "success": False,
            "error": "Failed to parse HTML with the given selectors",
            "result": {}
        }
    
    # Second attempt succeeds
    return {
        "success": True,
        "result": {
            "title": "测试文章标题",
            "date": "2025-02-25 08:30",
            "body": "这是一篇测试文章的内容。这是第一段。 这是第二段内容。 这是第三段内容。"
        }
    }

def simulate_url_parser_flow():
    """
    Simulate the flow of using LLM wrapper for URL parsing with real LLM responses.
    
    This function creates an LLM wrapper with a system prompt that guides the LLM
    to act as a specialized agent for parsing web URLs. It then simulates a conversation
    where the user provides a URL, the LLM analyzes it, creates a parser, tests it,
    and handles various user inputs including unrelated requests.
    
    The function uses mocked function calls to simulate the fetch_webpage and parse_with_parser
    functions without actually making HTTP requests or parsing real HTML.
    """
    print("\n=== Simulating URL Parser Flow ===")
    
    # Create a system prompt for the URL parser agent
    system_prompt = """You are a specialized agent designed to create parsers for web pages.
You MUST use memory operations to store and retrieve data. Here's how:

Memory Operations:
1. Store values:
<mem_set>{"key": "value"}</mem_set>
2. Get values:
<mem_get>key</mem_get>
3. Memory state will be shown:
<mem>{"key": "value"}</mem>

When user provides a URL, follow these steps EXACTLY:
1. Store URL:
<mem_set>{"url": "user_url"}</mem_set>

2. Fetch HTML and store it:
<mem_set>{"html": "content"}</mem_set>

3. Extract and store data:
<mem_set>{
    "title": "extracted_title",
    "date": "extracted_date",
    "body": "extracted_body"
}</mem_set>

4. When creating parser, store it:
<mem_set>{"parser_code": "def parse_page(html): ..."}</mem_set>

Example Flow:
User: "Parse this URL: example.com"
You: <mem_set>{"url": "example.com"}</mem_set>
I'll fetch and analyze that webpage.

User: "What did you find?"
You: <mem_get>url</mem_get>
<mem>{"url": "example.com"}</mem>
I found several interesting elements...

User: "Create a parser"
You: <mem_set>{"parser_code": "def parse_page(html): ..."}</mem_set>
I've created a parser based on the page structure.

CRITICAL RULES:
- ALWAYS use memory operations BEFORE your main response
- Store data IMMEDIATELY when you receive it
- Use memory operations for ALL data (url, html, title, date, body, parser_code)
- Keep responses natural and user-friendly
- Focus ONLY on web parsing tasks
- Politely decline unrelated requests

Common Memory Keys:
- url: The webpage URL
- html: The raw HTML content
- title: The page title
- date: Publication date
- body: Article body text
- parser_code: The generated parser code
- selectors: CSS selectors for parsing
"""
    
    # Create a wrapper with function calling enabled and focus mode on
    wrapper = LLMWrapper(
        system_prompt=system_prompt,
        focus_mode=True,
        enable_functions=True
    )
    
    # Define custom function schemas for the URL parser agent
    custom_schemas = [
        {
            "type": "function",
            "function": {
                "name": "fetch_webpage",
                "description": "Fetch the HTML content of a webpage",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The URL of the webpage to fetch"
                        }
                    },
                    "required": ["url"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "parse_with_parser",
                "description": "Parse HTML content with a parser",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "html": {
                            "type": "string",
                            "description": "The HTML content to parse"
                        },
                        "parser_name": {
                            "type": "string",
                            "description": "The name of the parser to use"
                        }
                    },
                    "required": ["html", "parser_name"]
                }
            }
        }
    ]
    
    # Patch the function manager to mock the function calls
    with patch.object(FunctionManager, 'execute_function') as mock_execute:
        # Set up the mock to return appropriate responses for different function calls
        def side_effect(function_name, args):
            if function_name == "fetch_webpage":
                return mock_fetch_webpage(args.get("url", ""))
            elif function_name == "parse_with_parser":
                parser_name = args.get("parser_name", "")
                return mock_parse_with_parser(args.get("html", ""), parser_name)
            return {"error": f"Unknown function: {function_name}"}
        
        mock_execute.side_effect = side_effect
        
        try:
            # Simulate the conversation flow
            print("\n=== Testing URL Parser Flow with Memory System ===")
            
            # Step 1: Initial greeting
            print("\n--- Step 1: Initial greeting ---")
            response = wrapper.chat(
                "Hello, I need help parsing a website",
                enable_functions=True,
                custom_function_schemas=custom_schemas,
                stream=False
            )
            print(f"LLM: {response.content}")
            
            # Step 2: Provide URL and verify memory storage
            print("\n--- Step 2: Provide URL and store in memory ---")
            response = wrapper.chat(
                "https://www.wenxuecity.com/news/2025/02/25/126034170.html",
                enable_functions=True,
                custom_function_schemas=custom_schemas,
                stream=False
            )
            print(f"LLM: {response.content}")
            print(f"Memory state: {json.dumps(wrapper.memory, indent=2)}")
            
            # Step 3: Confirm extracted data
            print("\n--- Step 3: Confirm extracted data ---")
            response = wrapper.chat(
                "Yes, the extracted data looks good",
                enable_functions=True,
                custom_function_schemas=custom_schemas,
                stream=False
            )
            print(f"LLM: {response.content}")
            print(f"Memory state: {json.dumps(wrapper.memory, indent=2)}")
            
            # Step 4: Test first parser attempt (will fail)
            print("\n--- Step 4: Test first parser attempt ---")
            response = wrapper.chat(
                "Yes, please test the parser with name 'first_attempt'",
                enable_functions=True,
                custom_function_schemas=custom_schemas,
                stream=False
            )
            print(f"LLM: {response.content}")
            
            # Step 5: Fix parser and test again
            print("\n--- Step 5: Fix parser and test again ---")
            response = wrapper.chat(
                "Please fix the parser and try again",
                enable_functions=True,
                custom_function_schemas=custom_schemas,
                stream=False
            )
            print(f"LLM: {response.content}")
            print(f"Memory state: {json.dumps(wrapper.memory, indent=2)}")
            
            # Step 6: Test unrelated request
            print("\n--- Step 6: Test unrelated request ---")
            response = wrapper.chat(
                "Can you help me book a flight to New York?",
                enable_functions=True,
                custom_function_schemas=custom_schemas,
                stream=False
            )
            print(f"LLM: {response.content}")
            
            # Step 7: Ask about other capabilities
            print("\n--- Step 7: Ask about other capabilities ---")
            response = wrapper.chat(
                "What else can I do with this parser?",
                enable_functions=True,
                custom_function_schemas=custom_schemas,
                stream=False
            )
            print(f"LLM: {response.content}")
            
            print("\n=== Test completed successfully ===")
            print(f"Final memory state: {json.dumps(wrapper.memory, indent=2)}")
            print(f"User-visible history length: {len(wrapper.history)}")
            print(f"Memory operations history length: {len(wrapper.memory_history)}")
            
        except Exception as e:
            print(f"\nError during test: {str(e)}")
            print("Memory state at error:")
            print(json.dumps(wrapper.memory, indent=2))
            raise

def test_url_parser_flow_with_mocked_responses():
    """
    Test the URL parser flow with mocked LLM responses.
    
    This function simulates the same conversation flow as simulate_url_parser_flow(),
    but uses predefined mocked responses instead of calling the actual LLM API.
    This is useful for testing the flow without incurring API costs or when
    the API is not available.
    """
    print("\n=== Testing URL Parser Flow with Mocked Responses ===")
    
    # Create a system prompt for the URL parser agent
    system_prompt = """
    You are a specialized agent designed to create parsers for web URLs.
    Your task is to help users extract structured data from web pages.
    """
    
    # Create a wrapper with mocked responses
    with patch('llm.llm_client.LLMClient.call_llm') as mock_call_llm:
        # Set up the mock to return predefined responses
        mock_responses = [
            # Step 1: Initial greeting
            MagicMock(content="Hello! I'm your web parsing assistant. Please provide a URL you'd like to parse, and I'll help you extract structured data from it."),
            
            # Step 2: After user provides URL
            MagicMock(content="I've fetched the webpage from @https://www.wenxuecity.com/news/2025/02/25/126034170.html and analyzed its structure.\n\nHere's what I found:\n\n- Title: 测试文章标题\n- Date: 2025-02-25 08:30\n- Body: 这是一篇测试文章的内容。这是第一段。 这是第二段内容。 这是第三段内容。\n\nDoes this look correct to you? If so, I can create a parser for this webpage."),
            
            # Step 3: After user confirms data
            MagicMock(content="Great! Based on my analysis, here's a parser for this webpage:\n\n```python\ndef parse_wenxuecity_article(html):\n    from bs4 import BeautifulSoup\n    \n    soup = BeautifulSoup(html, 'html.parser')\n    \n    # Extract title\n    title = soup.select_one('.news-title').text.strip()\n    \n    # Extract date\n    date = soup.select_one('.news-date').text.strip()\n    \n    # Extract body\n    body = soup.select_one('.news-content').text.strip()\n    \n    return {\n        'title': title,\n        'date': date,\n        'body': body\n    }\n```\n\nWould you like me to test this parser with the HTML we fetched?"),
            
            # Step 4: After user confirms to test parser (first attempt - fails)
            MagicMock(content="I tested the parser with the HTML, but it failed to extract the data correctly. The error was: 'Failed to parse HTML with the given selectors'.\n\nLet me analyze the HTML again and create an improved parser."),
            
            # Step 5: After user asks to fix parser
            MagicMock(content="I've created an improved parser with more robust selectors:\n\n```python\ndef parse_wenxuecity_article_improved(html):\n    from bs4 import BeautifulSoup\n    \n    soup = BeautifulSoup(html, 'html.parser')\n    \n    # Extract title with fallback selectors\n    title_element = soup.select_one('.news-title') or soup.select_one('h1') or soup.select_one('title')\n    title = title_element.text.strip() if title_element else ''\n    \n    # Extract date with fallback selectors\n    date_element = soup.select_one('.news-date') or soup.select_one('.date') or soup.select_one('time')\n    date = date_element.text.strip() if date_element else ''\n    \n    # Extract body with fallback selectors\n    body_element = soup.select_one('.news-content') or soup.select_one('article') or soup.select_one('.content')\n    body = body_element.text.strip() if body_element else ''\n    \n    return {\n        'title': title,\n        'date': date,\n        'body': body\n    }\n```\n\nWould you like me to test this improved parser?"),
            
            # Step 6: After user confirms to test improved parser
            MagicMock(content="Great news! The improved parser successfully extracted the data:\n\n- Title: 测试文章标题\n- Date: 2025-02-25 08:30\n- Body: 这是一篇测试文章的内容。这是第一段。 这是第二段内容。 这是第三段内容。\n\nThe parser is working correctly now. What would you like to do next?"),
            
            # Step 7: After user asks for unrelated task
            MagicMock(content="I'm sorry, but as a specialized web parsing agent, I can't help with booking flights. My capabilities are limited to helping you parse and extract data from websites. Is there anything else you'd like to do with the parser or another website you'd like to parse?"),
            
            # Step 8: After user asks what else can be done
            MagicMock(content="Here are some things you can do with this parser:\n\n1. Parse other similar pages from the same website\n2. Modify the parser to extract additional data fields\n3. Save the parser for future use\n4. Create a new parser for a different website\n5. Use the parser to extract data from multiple pages\n\nWhat would you like to do?")
        ]
        
        mock_call_llm.side_effect = mock_responses
        
        # Create the wrapper
        wrapper = LLMWrapper(
            system_prompt=system_prompt,
            focus_mode=True,
            enable_functions=True
        )
        
        # Simulate the conversation flow with predefined responses
        
        # Step 1: Initial greeting
        print("\n--- Step 1: Initial greeting ---")
        response = wrapper.chat("Hello, I need help parsing a website", stream=False)
        print(f"LLM: {response.content}")
        
        # Step 2: User provides a URL
        print("\n--- Step 2: User provides a URL ---")
        response = wrapper.chat("@https://www.wenxuecity.com/news/2025/02/25/126034170.html", stream=False)
        print(f"LLM: {response.content}")
        
        # Step 3: User confirms the extracted data
        print("\n--- Step 3: User confirms the extracted data ---")
        response = wrapper.chat("Yes, the title, body, and date look good", stream=False)
        print(f"LLM: {response.content}")
        
        # Step 4: User confirms to test the parser (first attempt - will fail)
        print("\n--- Step 4: User confirms to test the parser (first attempt) ---")
        response = wrapper.chat("Yes, please test the parser", stream=False)
        print(f"LLM: {response.content}")
        
        # Step 5: User asks to fix the parser
        print("\n--- Step 5: User asks to fix the parser ---")
        response = wrapper.chat("Please fix the parser and try again", stream=False)
        print(f"LLM: {response.content}")
        
        # Step 6: User confirms to test the improved parser
        print("\n--- Step 6: User confirms to test the improved parser ---")
        response = wrapper.chat("Yes, please test the improved parser", stream=False)
        print(f"LLM: {response.content}")
        
        # Step 7: User asks for an unrelated task
        print("\n--- Step 7: User asks for an unrelated task ---")
        response = wrapper.chat("Can you help me book a flight to New York?", stream=False)
        print(f"LLM: {response.content}")
        
        # Step 8: User asks what else can be done
        print("\n--- Step 8: User asks what else can be done ---")
        response = wrapper.chat("What else can I do with this parser?", stream=False)
        print(f"LLM: {response.content}")

def main():
    """
    Main function to run the URL parser flow tests.
    
    This function first attempts to run the test with real LLM responses.
    If that fails (e.g., due to missing API keys or rate limits),
    it falls back to using mocked responses.
    """
    print("=== URL Parser Flow Test ===")
    print("This test simulates the flow of using LLM wrapper for parsing a URL.")
    print("It demonstrates how the LLM can:")
    print("1. Ask for a URL")
    print("2. Retrieve and analyze HTML")
    print("3. Create a parser")
    print("4. Test and improve the parser")
    print("5. Handle unrelated requests in focus mode")
    print("\nRunning test...")
    
    # Run the simulation with real LLM responses (if available)
    try:
        simulate_url_parser_flow()
    except Exception as e:
        print(f"\nError in simulate_url_parser_flow: {str(e)}")
        print("Falling back to mocked responses...")
    
    # Run the test with mocked LLM responses
    test_url_parser_flow_with_mocked_responses()
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    main() 