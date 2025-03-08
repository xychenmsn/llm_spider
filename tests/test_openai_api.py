#!/usr/bin/env python3
"""
Simple script to test OpenAI API connectivity.
This script loads the API key from .env and makes a simple test call.
"""

import os
import sys
from pathlib import Path
import openai
from dotenv import load_dotenv

# Add the project root to the path so we can import from the project
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def test_openai_api():
    """Test the OpenAI API with a simple completion request."""
    # Load environment variables from .env file
    load_dotenv()
    
    # Get the API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment variables.")
        print("Make sure your .env file contains a valid API key.")
        return False
    
    # Initialize the OpenAI client
    client = openai.OpenAI(api_key=api_key)
    
    try:
        # Make a simple test request
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, are you working correctly?"}
            ],
            max_tokens=50
        )
        
        # Print the response
        print("\n=== API Test Successful ===")
        print(f"Model: {response.model}")
        print(f"Response: {response.choices[0].message.content}")
        print("===========================\n")
        return True
        
    except Exception as e:
        print("\n=== API Test Failed ===")
        print(f"Error: {str(e)}")
        print("=======================\n")
        return False

if __name__ == "__main__":
    print("Testing OpenAI API connection...")
    success = test_openai_api()
    if success:
        print("✅ OpenAI API is working correctly!")
    else:
        print("❌ OpenAI API test failed. Check the error message above.") 