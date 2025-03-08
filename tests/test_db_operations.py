#!/usr/bin/env python3
"""
Test script for database operations utility functions.

This script demonstrates the usage of the database operations utility functions.
"""

import sys
import json
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from db.db_operations import (
    get_all_url_parsers,
    get_url_parser_by_id,
    get_url_parser_by_name,
    find_parser_for_url,
    create_url_parser,
    update_url_parser,
    delete_url_parser
)

def test_get_all_parsers():
    """Test retrieving all URL parsers."""
    print("\n=== Testing get_all_url_parsers() ===")
    parsers = get_all_url_parsers()
    print(f"Found {len(parsers)} parsers:")
    for parser in parsers:
        print(f"  - {parser.id}: {parser.name} ({parser.url_pattern})")
    return parsers

def test_get_parser_by_name():
    """Test retrieving a URL parser by name."""
    print("\n=== Testing get_url_parser_by_name() ===")
    parser = get_url_parser_by_name("GitHub Repository")
    if parser:
        print(f"Found parser with name 'GitHub Repository':")
        print(f"  - ID: {parser.id}")
        print(f"  - URL Pattern: {parser.url_pattern}")
        print(f"  - Parser: {parser.parser}")
    else:
        print("No parser found with name 'GitHub Repository'")
    return parser

def test_find_parser_for_url():
    """Test finding a parser for a URL."""
    print("\n=== Testing find_parser_for_url() ===")
    
    # Test GitHub URL
    github_url = "https://github.com/username/repo"
    parser = find_parser_for_url(github_url)
    if parser:
        print(f"Found parser for URL '{github_url}':")
        print(f"  - {parser.id}: {parser.name} ({parser.url_pattern})")
    else:
        print(f"No parser found for URL '{github_url}'")
    
    # Test Medium URL
    medium_url = "https://medium.com/some-article"
    parser = find_parser_for_url(medium_url)
    if parser:
        print(f"Found parser for URL '{medium_url}':")
        print(f"  - {parser.id}: {parser.name} ({parser.url_pattern})")
    else:
        print(f"No parser found for URL '{medium_url}'")
    
    # Test non-matching URL
    non_matching_url = "https://example.com"
    parser = find_parser_for_url(non_matching_url)
    if parser:
        print(f"Found parser for URL '{non_matching_url}':")
        print(f"  - {parser.id}: {parser.name} ({parser.url_pattern})")
    else:
        print(f"No parser found for URL '{non_matching_url}'")

def test_create_parser():
    """Test creating a new URL parser."""
    print("\n=== Testing create_url_parser() ===")
    
    # Create a new parser
    new_parser = create_url_parser(
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
    
    if new_parser:
        print(f"Created parser with ID: {new_parser.id}")
        print(f"Name: {new_parser.name}")
        print(f"URL Pattern: {new_parser.url_pattern}")
        return new_parser.id
    else:
        print("Failed to create parser")
        return None

def test_update_parser(parser_id):
    """Test updating a URL parser."""
    print(f"\n=== Testing update_url_parser({parser_id}) ===")
    
    # Update the parser
    updated_parser = update_url_parser(
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
        print(f"Failed to update parser with ID {parser_id}")

def test_delete_parser(parser_id):
    """Test deleting a URL parser."""
    print(f"\n=== Testing delete_url_parser({parser_id}) ===")
    
    # Delete the parser
    success = delete_url_parser(parser_id)
    if success:
        print(f"Successfully deleted parser with ID: {parser_id}")
    else:
        print(f"Failed to delete parser with ID {parser_id}")
    
    # Verify deletion
    parser = get_url_parser_by_id(parser_id)
    if parser:
        print(f"ERROR: Parser with ID {parser_id} still exists!")
    else:
        print(f"Verified: Parser with ID {parser_id} no longer exists.")

def main():
    """Run the database operations tests."""
    print("=== Starting Database Operations Tests ===")
    
    # Test getting all parsers
    test_get_all_parsers()
    
    # Test getting a parser by name
    test_get_parser_by_name()
    
    # Test finding a parser for a URL
    test_find_parser_for_url()
    
    # Test creating a new parser
    parser_id = test_create_parser()
    if parser_id:
        # Test updating the parser
        test_update_parser(parser_id)
        
        # Test deleting the parser
        test_delete_parser(parser_id)
    
    print("\n=== Database Operations Tests Complete ===")

if __name__ == "__main__":
    main() 