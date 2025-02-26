#!/usr/bin/env python3
"""
Initialize the database with initial data.

This script creates the database tables and populates them with initial data.
"""

import sys
import json
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from db.models import Base, URLParser, get_engine
from db.db_client import db_client

def init_db():
    """Initialize the database."""
    print("Initializing database...")
    
    # Create tables
    engine = get_engine()
    Base.metadata.create_all(engine)
    
    # Add initial URL parsers
    add_initial_url_parsers()
    
    print("Database initialization complete.")

def add_initial_url_parsers():
    """Add initial URL parsers to the database."""
    print("Adding initial URL parsers...")
    
    # Check if parsers already exist
    existing_parsers = db_client.get_all(URLParser)
    if existing_parsers:
        print(f"Found {len(existing_parsers)} existing parsers. Skipping initialization.")
        return
    
    # GitHub repository parser
    github_repo_parser = URLParser(
        name="GitHub Repository",
        url_pattern=r"https://github\.com/([^/]+)/([^/]+)/?$",
        parser="github_repo_parser",
        meta_data={
            "site": "github.com",
            "type": "repository"
        },
        chat_data={
            "system_prompt": "You are analyzing a GitHub repository.",
            "user_prompt_template": "Please summarize this GitHub repository: {url}"
        }
    )
    
    # Medium article parser
    medium_article_parser = URLParser(
        name="Medium Article",
        url_pattern=r"https://medium\.com/.*",
        parser="medium_article_parser",
        meta_data={
            "site": "medium.com",
            "type": "article"
        },
        chat_data={
            "system_prompt": "You are analyzing a Medium article.",
            "user_prompt_template": "Please summarize this Medium article: {url}"
        }
    )
    
    # Add parsers to the database
    db_client.create(github_repo_parser)
    db_client.create(medium_article_parser)
    
    print("Initial URL parsers added.")

if __name__ == "__main__":
    init_db() 