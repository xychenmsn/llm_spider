"""
Database package for LLM Spider.
"""

# Import key components for easier access
from db.models import Base, URLParser
from db.db_client import db_client
from db.db_operations import (
    get_all_url_parsers,
    get_url_parser_by_id,
    get_url_parser_by_name,
    find_parser_for_url,
    create_url_parser,
    update_url_parser,
    delete_url_parser
) 