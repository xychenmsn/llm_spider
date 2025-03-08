#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for gpt-4o-mini model
"""

import os
import sys
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

# Configure OpenAI
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("Error: OPENAI_API_KEY not found in environment variables.")
    sys.exit(1)

# Initialize the OpenAI client
try:
    print("Initializing OpenAI client...")
    client = openai.OpenAI(api_key=api_key)
    
    # Test the gpt-4o-mini model
    print("Testing gpt-4o-mini model...")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello! Can you tell me if you're the gpt-4o-mini model?"}
        ],
        max_tokens=100
    )
    
    # Print the response
    print("\nResponse from gpt-4o-mini:")
    print(response.choices[0].message.content)
    print("\nModel used:", response.model)
    print("Success! The gpt-4o-mini model is available.")
    
except Exception as e:
    print(f"Error: {str(e)}")
    print("The gpt-4o-mini model might not be available or there's an issue with your API key.") 