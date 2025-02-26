#!/usr/bin/env python3
"""
Script to populate the database with sample URL parser records.

This script deletes all existing URL parser records and adds 40 sample records for testing and development.
"""

import sys
import json
import random
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from db.models import URLParser
from db.db_client import db_client
from sqlalchemy import delete

def clear_url_parsers():
    """Delete all URL parser records from the database."""
    print("Deleting all existing URL parser records...")
    
    with db_client.session_scope() as session:
        # Delete all records from url_parser table
        delete_stmt = delete(URLParser)
        result = session.execute(delete_stmt)
        print(f"Deleted {result.rowcount} URL parser records.")

def populate_url_parsers(count=40):
    """Add sample URL parser records to the database.
    
    Args:
        count: Number of sample records to create
    """
    print(f"Adding {count} sample URL parser records...")
    
    # Base sample URL parsers
    base_parsers = [
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
    
    # Additional site types to generate more variety
    additional_sites = [
        {"name": "LinkedIn Post", "domain": "linkedin.com", "type": "post"},
        {"name": "Facebook Post", "domain": "facebook.com", "type": "post"},
        {"name": "Instagram Post", "domain": "instagram.com", "type": "post"},
        {"name": "TikTok Video", "domain": "tiktok.com", "type": "video"},
        {"name": "Substack Article", "domain": "substack.com", "type": "article"},
        {"name": "Dev.to Article", "domain": "dev.to", "type": "article"},
        {"name": "Hashnode Article", "domain": "hashnode.com", "type": "article"},
        {"name": "Product Hunt Product", "domain": "producthunt.com", "type": "product"},
        {"name": "Kaggle Dataset", "domain": "kaggle.com", "type": "dataset"},
        {"name": "Hugging Face Model", "domain": "huggingface.co", "type": "model"},
        {"name": "NPM Package", "domain": "npmjs.com", "type": "package"},
        {"name": "PyPI Package", "domain": "pypi.org", "type": "package"},
        {"name": "Coursera Course", "domain": "coursera.org", "type": "course"},
        {"name": "Udemy Course", "domain": "udemy.com", "type": "course"},
        {"name": "edX Course", "domain": "edx.org", "type": "course"}
    ]
    
    # Generate sample parsers
    sample_parsers = []
    
    # First add the base parsers
    sample_parsers.extend(base_parsers)
    
    # Then generate additional parsers to reach the desired count
    while len(sample_parsers) < count:
        # Pick a random site from additional sites
        site = random.choice(additional_sites)
        
        # Create a unique variant name
        variant = f" Variant {random.randint(1, 10000)}"
        name = f"{site['name']}{variant}"
        
        # Ensure the name is unique
        while any(p["name"] == name for p in sample_parsers):
            variant = f" Variant {random.randint(1, 10000)}"
            name = f"{site['name']}{variant}"
        
        parser_data = {
            "name": name,
            "url_pattern": f"https://(?:www\\.)?{site['domain']}/.*",
            "parser": f"{site['domain'].split('.')[0]}_{site['type']}_parser",
            "meta_data": {
                "site": site["domain"],
                "type": site["type"],
                "extract_content": True,
                "extract_metadata": random.choice([True, False]),
                "priority": random.randint(1, 5)
            },
            "chat_data": {
                "system_prompt": f"You are analyzing a {site['name']}.",
                "user_prompt_template": f"Please analyze this {site['name']}: {{url}}",
                "temperature": round(random.uniform(0.1, 0.9), 1)
            }
        }
        
        sample_parsers.append(parser_data)
    
    # Ensure we only have the requested number of parsers
    sample_parsers = sample_parsers[:count]
    
    # Add each parser
    added_count = 0
    for parser_data in sample_parsers:
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
    
    # Clear existing URL parsers
    clear_url_parsers()
    
    # Populate URL parsers
    populate_url_parsers(40)
    
    # Get all parsers to verify
    parsers = db_client.get_all(URLParser)
    print(f"\nTotal URL parsers in database: {len(parsers)}")
    
    # Print first 5 parsers
    print("First 5 parsers:")
    for parser in parsers[:5]:
        print(f"  - {parser.id}: {parser.name} ({parser.parser})")
    
    print("..." if len(parsers) > 5 else "")
    
    print("=" * 80)
    print("Database population complete.")
    print("=" * 80)

if __name__ == "__main__":
    main() 