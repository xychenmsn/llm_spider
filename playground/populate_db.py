#!/usr/bin/env python3
"""
Script to populate the database with sample URL parser records.

This script adds 10 sample URL parser records to the database for testing and development.
"""

import sys
import json
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from db.models import URLParser
from db.db_client import db_client
from db.db_operations import get_url_parser_by_name

def populate_url_parsers():
    """Add sample URL parser records to the database."""
    print("Adding sample URL parser records...")
    
    # Sample URL parsers
    sample_parsers = [
        {
            "name": "GitHub Repository",
            "url_pattern": r"https://github\.com/([^/]+)/([^/]+)/?$",
            "parser": "github_repo_parser",
            "meta_data": {
                "site": "github.com",
                "type": "repository",
                "extract_readme": True,
                "extract_issues": False
            },
            "chat_data": {
                "system_prompt": "You are analyzing a GitHub repository.",
                "user_prompt_template": "Please summarize this GitHub repository: {url}"
            }
        },
        {
            "name": "Medium Article",
            "url_pattern": r"https://medium\.com/.*",
            "parser": "medium_article_parser",
            "meta_data": {
                "site": "medium.com",
                "type": "article",
                "extract_comments": True
            },
            "chat_data": {
                "system_prompt": "You are analyzing a Medium article.",
                "user_prompt_template": "Please summarize this Medium article: {url}"
            }
        },
        {
            "name": "Stack Overflow Question",
            "url_pattern": r"https://stackoverflow\.com/questions/\d+/[^/]+/?$",
            "parser": "stackoverflow_parser",
            "meta_data": {
                "site": "stackoverflow.com",
                "type": "question",
                "extract_answers": True,
                "extract_comments": True
            },
            "chat_data": {
                "system_prompt": "You are analyzing a Stack Overflow question.",
                "user_prompt_template": "Please analyze this Stack Overflow question: {url}"
            }
        },
        {
            "name": "YouTube Video",
            "url_pattern": r"https://(?:www\.)?youtube\.com/watch\?v=[\w-]+",
            "parser": "youtube_video_parser",
            "meta_data": {
                "site": "youtube.com",
                "type": "video",
                "extract_transcript": True,
                "extract_comments": False
            },
            "chat_data": {
                "system_prompt": "You are analyzing a YouTube video.",
                "user_prompt_template": "Please summarize this YouTube video: {url}"
            }
        },
        {
            "name": "Twitter/X Post",
            "url_pattern": r"https://(?:www\.)?(?:twitter|x)\.com/\w+/status/\d+",
            "parser": "twitter_post_parser",
            "meta_data": {
                "site": "twitter.com",
                "type": "post",
                "extract_replies": True,
                "extract_media": True
            },
            "chat_data": {
                "system_prompt": "You are analyzing a Twitter/X post.",
                "user_prompt_template": "Please analyze this Twitter/X post: {url}"
            }
        },
        {
            "name": "Reddit Post",
            "url_pattern": r"https://(?:www\.)?reddit\.com/r/[^/]+/comments/[\w-]+/[\w-]+/?",
            "parser": "reddit_post_parser",
            "meta_data": {
                "site": "reddit.com",
                "type": "post",
                "extract_comments": True,
                "extract_media": True
            },
            "chat_data": {
                "system_prompt": "You are analyzing a Reddit post.",
                "user_prompt_template": "Please analyze this Reddit post: {url}"
            }
        },
        {
            "name": "HackerNews Post",
            "url_pattern": r"https://news\.ycombinator\.com/item\?id=\d+",
            "parser": "hackernews_post_parser",
            "meta_data": {
                "site": "news.ycombinator.com",
                "type": "post",
                "extract_comments": True
            },
            "chat_data": {
                "system_prompt": "You are analyzing a HackerNews post.",
                "user_prompt_template": "Please analyze this HackerNews post: {url}"
            }
        },
        {
            "name": "Wikipedia Article",
            "url_pattern": r"https://(?:[\w-]+\.)?wikipedia\.org/wiki/[\w%]+",
            "parser": "wikipedia_article_parser",
            "meta_data": {
                "site": "wikipedia.org",
                "type": "article",
                "extract_references": True,
                "extract_sections": True
            },
            "chat_data": {
                "system_prompt": "You are analyzing a Wikipedia article.",
                "user_prompt_template": "Please summarize this Wikipedia article: {url}"
            }
        },
        {
            "name": "ArXiv Paper",
            "url_pattern": r"https://arxiv\.org/(?:abs|pdf)/\d+\.\d+(?:v\d+)?",
            "parser": "arxiv_paper_parser",
            "meta_data": {
                "site": "arxiv.org",
                "type": "paper",
                "extract_abstract": True,
                "extract_references": False
            },
            "chat_data": {
                "system_prompt": "You are analyzing an ArXiv paper.",
                "user_prompt_template": "Please summarize this ArXiv paper: {url}"
            }
        },
        {
            "name": "Google Scholar Article",
            "url_pattern": r"https://scholar\.google\.com/scholar\?cluster=\d+",
            "parser": "google_scholar_parser",
            "meta_data": {
                "site": "scholar.google.com",
                "type": "article",
                "extract_citations": True,
                "extract_related": True
            },
            "chat_data": {
                "system_prompt": "You are analyzing a scholarly article.",
                "user_prompt_template": "Please summarize this scholarly article: {url}"
            }
        }
    ]
    
    # Add each parser if it doesn't already exist
    added_count = 0
    for parser_data in sample_parsers:
        # Check if parser already exists
        existing_parser = get_url_parser_by_name(parser_data["name"])
        if existing_parser:
            print(f"  - {parser_data['name']} already exists, skipping...")
            continue
        
        # Create new parser
        new_parser = URLParser(
            name=parser_data["name"],
            url_pattern=parser_data["url_pattern"],
            parser=parser_data["parser"],
            meta_data=parser_data["meta_data"],
            chat_data=parser_data["chat_data"]
        )
        
        created_parser = db_client.create(new_parser)
        if created_parser:
            print(f"  + Added: {created_parser.name} (ID: {created_parser.id})")
            added_count += 1
        else:
            print(f"  ! Failed to add: {parser_data['name']}")
    
    print(f"Added {added_count} new URL parser records.")

def main():
    """Run the database population script."""
    print("=" * 80)
    print("DATABASE POPULATION SCRIPT")
    print("=" * 80)
    
    # Populate URL parsers
    populate_url_parsers()
    
    # Get all parsers to verify
    parsers = db_client.get_all(URLParser)
    print(f"\nTotal URL parsers in database: {len(parsers)}")
    for parser in parsers:
        print(f"  - {parser.id}: {parser.name} ({parser.parser})")
    
    print("=" * 80)
    print("Database population complete.")
    print("=" * 80)

if __name__ == "__main__":
    main() 