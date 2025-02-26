#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for the database functionality.
"""

import sys
import json
from pathlib import Path

# Add the parent directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent))

from db.models import URLParser
from db.db_client import db_client

def print_separator():
    print("-" * 80)

def test_get_all_parsers():
    """Test retrieving all URL parsers."""
    print("Getting all URL parsers:")
    parsers = db_client.get_all(URLParser)
    for parser in parsers:
        print(f"  - {parser.name}: {parser.url_pattern} (Parser: {parser.parser})")
    return parsers

def test_add_parser():
    """Test adding a new URL parser."""
    print("\nAdding a new URL parser:")
    new_parser = URLParser(
        name="Stack Overflow Question",
        url_pattern=r"https://stackoverflow\.com/questions/\d+/.*",
        parser="stackoverflow_parser",
        meta_data={
            "extract_answers": True,
            "extract_comments": True
        },
        chat_data={
            "system_prompt": "You are analyzing a Stack Overflow question. Provide insights about the question and its answers."
        }
    )
    
    created_parser = db_client.create(new_parser)
    print(f"  Added: {created_parser.name} (ID: {created_parser.id})")
    
    return created_parser.id

def test_get_parser_by_id(parser_id):
    """Test retrieving a URL parser by ID."""
    print(f"\nGetting URL parser with ID {parser_id}:")
    parser = db_client.get_by_id(URLParser, parser_id)
    if parser:
        print(f"  Found: {parser.name} (Pattern: {parser.url_pattern})")
        print(f"  Meta data: {parser.meta_data}")
        print(f"  Chat data: {parser.chat_data}")
    else:
        print(f"  No parser found with ID {parser_id}")
    return parser_id if parser else None

def test_update_parser(parser_id):
    """Test updating a URL parser."""
    print(f"\nUpdating URL parser with ID {parser_id}:")
    updated_parser = db_client.update(
        URLParser, 
        parser_id,
        url_pattern=r"https://stackoverflow\.com/questions/\d+/[^/]+/?$",
        meta_data={
            "extract_answers": True,
            "extract_comments": True,
            "extract_related": True
        }
    )
    
    if updated_parser:
        print(f"  Updated: {updated_parser.name}")
        print(f"  New pattern: {updated_parser.url_pattern}")
        print(f"  New meta data: {updated_parser.meta_data}")
    else:
        print(f"  No parser found with ID {parser_id}")
    
    return parser_id if updated_parser else None

def test_delete_parser(parser_id):
    """Test deleting a URL parser."""
    print(f"\nDeleting URL parser with ID {parser_id}:")
    success = db_client.delete(URLParser, parser_id)
    if success:
        print(f"  Successfully deleted parser with ID {parser_id}")
    else:
        print(f"  No parser found with ID {parser_id}")
    return success

def main():
    """Run the database tests."""
    print_separator()
    print("TESTING DATABASE FUNCTIONALITY")
    print_separator()
    
    # Test getting all parsers
    parsers = test_get_all_parsers()
    
    # Test adding a new parser
    parser_id = test_add_parser()
    
    # Test getting a parser by ID
    test_get_parser_by_id(parser_id)
    
    # Test updating a parser
    test_update_parser(parser_id)
    
    # Test getting the updated parser
    test_get_parser_by_id(parser_id)
    
    # Test deleting a parser
    test_delete_parser(parser_id)
    
    # Verify deletion
    test_get_parser_by_id(parser_id)
    
    print_separator()
    print("Database tests completed.")
    print_separator()

if __name__ == "__main__":
    main() 