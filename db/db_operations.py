"""
Database operations utility functions.

This module provides utility functions for common database operations
using the DBClient.
"""

import re
import logging
from typing import List, Optional, Dict, Any, Union

from db.models import URLParser
from db.db_client import db_client

# Set up logging
logger = logging.getLogger(__name__)

def get_all_url_parsers() -> List[URLParser]:
    """
    Get all URL parsers from the database.
    
    Returns:
        List of URLParser objects
    """
    try:
        return db_client.get_all(URLParser)
    except Exception as e:
        logger.error(f"Error getting all URL parsers: {str(e)}")
        return []

def get_url_parser_by_id(parser_id: int) -> Optional[URLParser]:
    """
    Get a URL parser by its ID.
    
    Args:
        parser_id: ID of the parser to retrieve
        
    Returns:
        URLParser object if found, None otherwise
    """
    try:
        return db_client.get_by_id(URLParser, parser_id)
    except Exception as e:
        logger.error(f"Error getting URL parser with ID {parser_id}: {str(e)}")
        return None

def get_url_parser_by_name(name: str) -> Optional[URLParser]:
    """
    Get a URL parser by its name.
    
    Args:
        name: Name of the parser to retrieve
        
    Returns:
        URLParser object if found, None otherwise
    """
    try:
        parsers = db_client.query(URLParser, name=name)
        return parsers[0] if parsers else None
    except Exception as e:
        logger.error(f"Error getting URL parser with name '{name}': {str(e)}")
        return None

def find_parser_for_url(url: str) -> Optional[URLParser]:
    """
    Find a parser that matches the given URL.
    
    Args:
        url: URL to find a parser for
        
    Returns:
        URLParser object if a matching parser is found, None otherwise
    """
    try:
        parsers = db_client.get_all(URLParser)
        for parser in parsers:
            if re.match(parser.url_pattern, url):
                return parser
        return None
    except Exception as e:
        logger.error(f"Error finding parser for URL '{url}': {str(e)}")
        return None

def create_url_parser(
    name: str,
    url_pattern: str,
    parser: str,
    meta_data: Dict[str, Any] = None,
    chat_data: Dict[str, Any] = None
) -> Optional[URLParser]:
    """
    Create a new URL parser.
    
    Args:
        name: Name of the parser
        url_pattern: Regex pattern for matching URLs
        parser: Name of the parser function
        meta_data: Metadata for the parser
        chat_data: Chat data for the parser
        
    Returns:
        Created URLParser object if successful, None otherwise
    """
    try:
        new_parser = URLParser(
            name=name,
            url_pattern=url_pattern,
            parser=parser,
            meta_data=meta_data or {},
            chat_data=chat_data or {}
        )
        return db_client.create(new_parser)
    except Exception as e:
        logger.error(f"Error creating URL parser '{name}': {str(e)}")
        return None

def update_url_parser(
    parser_id: int,
    **kwargs
) -> Optional[URLParser]:
    """
    Update an existing URL parser.
    
    Args:
        parser_id: ID of the parser to update
        **kwargs: Fields to update
        
    Returns:
        Updated URLParser object if successful, None otherwise
    """
    try:
        return db_client.update(URLParser, parser_id, **kwargs)
    except Exception as e:
        logger.error(f"Error updating URL parser with ID {parser_id}: {str(e)}")
        return None

def delete_url_parser(parser_id: int) -> bool:
    """
    Delete a URL parser.
    
    Args:
        parser_id: ID of the parser to delete
        
    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        return db_client.delete(URLParser, parser_id)
    except Exception as e:
        logger.error(f"Error deleting URL parser with ID {parser_id}: {str(e)}")
        return False 