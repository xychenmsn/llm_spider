#!/usr/bin/env python3
"""
Test script for the DBClient class.

This script demonstrates the usage of the DBClient class for database operations.
"""

import sys
import json
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from db.models import URLParser
from db.db_client import db_client

def test_get_all_parsers():
    """Test retrieving all URL parsers."""
    print("\n=== Testing get_all() ===")
    parsers = db_client.get_all(URLParser)
    print(f"Found {len(parsers)} parsers:")
    for parser in parsers:
        print(f"  - {parser.id}: {parser.name} ({parser.url_pattern})")
    return parsers

def test_add_parser():
    """Test adding a new URL parser."""
    print("\n=== Testing create() ===")
    
    # Create a new parser
    new_parser = URLParser(
        name="Stack Overflow Question",
        url_pattern=r"^https?://stackoverflow\.com/questions/\d+/[\w-]+$",
        parser="stack_overflow_parser",
        meta_data={
            "site": "stackoverflow.com",
            "type": "question",
            "tags": ["programming", "q&a"]
        },
        chat_data={
            "system_prompt": "You are analyzing a Stack Overflow question.",
            "user_prompt_template": "Please summarize this Stack Overflow question: {url}"
        }
    )
    
    # Add the parser to the database
    created_parser = db_client.create(new_parser)
    print(f"Added parser with ID: {created_parser.id}")
    print(f"Name: {created_parser.name}")
    print(f"URL Pattern: {created_parser.url_pattern}")
    
    return created_parser.id

def test_get_parser_by_id(parser_id):
    """Test retrieving a URL parser by ID."""
    print(f"\n=== Testing get_by_id({parser_id}) ===")
    
    parser = db_client.get_by_id(URLParser, parser_id)
    if parser:
        print(f"Found parser with ID: {parser.id}")
        print(f"Name: {parser.name}")
        print(f"URL Pattern: {parser.url_pattern}")
        print(f"Parser: {parser.parser}")
        print(f"Meta Data: {parser.meta_data}")
        print(f"Chat Data: {parser.chat_data}")
    else:
        print(f"No parser found with ID: {parser_id}")
    
    return parser

def test_update_parser(parser_id):
    """Test updating a URL parser."""
    print(f"\n=== Testing update({parser_id}) ===")
    
    # Update the parser
    updated_parser = db_client.update(
        URLParser, 
        parser_id,
        url_pattern=r"^https?://stackoverflow\.com/questions/\d+/[\w-]+(?:\?[\w=&]+)?$",
        meta_data={
            "site": "stackoverflow.com",
            "type": "question",
            "tags": ["programming", "q&a", "coding"]
        }
    )
    
    if updated_parser:
        print(f"Updated parser with ID: {updated_parser.id}")
        print(f"New URL Pattern: {updated_parser.url_pattern}")
        print(f"New Meta Data: {updated_parser.meta_data}")
    else:
        print(f"No parser found with ID: {parser_id}")
    
    return updated_parser

def test_query_parsers():
    """Test querying parsers with filters."""
    print("\n=== Testing query() ===")
    
    parsers = db_client.query(URLParser, name="GitHub Repository")
    print(f"Found {len(parsers)} parsers with name 'GitHub Repository':")
    for parser in parsers:
        print(f"  - {parser.id}: {parser.name} ({parser.url_pattern})")
    
    return parsers

def test_delete_parser(parser_id):
    """Test deleting a URL parser."""
    print(f"\n=== Testing delete({parser_id}) ===")
    
    # Delete the parser
    success = db_client.delete(URLParser, parser_id)
    if success:
        print(f"Successfully deleted parser with ID: {parser_id}")
    else:
        print(f"No parser found with ID: {parser_id}")
    
    # Verify deletion
    parser = db_client.get_by_id(URLParser, parser_id)
    if parser:
        print(f"ERROR: Parser with ID {parser_id} still exists!")
    else:
        print(f"Verified: Parser with ID {parser_id} no longer exists.")
    
    return success

def main():
    """Run the database tests."""
    print("=== Starting Database Client Tests ===")
    
    # Test getting all parsers
    parsers = test_get_all_parsers()
    
    # Test adding a new parser
    parser_id = test_add_parser()
    
    # Test getting a parser by ID
    parser = test_get_parser_by_id(parser_id)
    
    # Test querying parsers
    test_query_parsers()
    
    # Test updating a parser
    updated_parser = test_update_parser(parser_id)
    
    # Test getting the updated parser
    test_get_parser_by_id(parser_id)
    
    # Test deleting a parser
    test_delete_parser(parser_id)
    
    print("\n=== Database Client Tests Complete ===")

if __name__ == "__main__":
    main() 