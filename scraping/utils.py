#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - Web Scraping Utilities

This module provides utilities for web scraping in the LLM Spider application.
"""

import base64
import logging
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# Set up logging
logger = logging.getLogger(__name__)


def fetch_webpage_html(url: str) -> str:
    """Fetch the HTML content of a webpage using requests."""
    try:
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        response.raise_for_status()
        return response.text
    except Exception as e:
        logger.error(f"Error fetching HTML: {str(e)}")
        return f"Error fetching HTML: {str(e)}"


def take_webpage_screenshot(url: str, timeout: int = 15000) -> Optional[str]:
    """Take a screenshot of a webpage using Playwright and return as base64."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            
            # Set a shorter timeout
            page.goto(url, timeout=timeout)
            
            # Wait for the page to load, but with a timeout
            try:
                page.wait_for_load_state("networkidle", timeout=timeout)
            except Exception as e:
                logger.warning(f"Timeout waiting for page to load: {str(e)}")
                # Continue anyway, we'll take a screenshot of what we have
            
            # Take a screenshot of the full page
            screenshot_bytes = page.screenshot(full_page=True, type='jpeg', quality=50)
            browser.close()
            
            # Convert to base64
            return base64.b64encode(screenshot_bytes).decode('utf-8')
    except Exception as e:
        logger.error(f"Error taking screenshot: {str(e)}")
        return None


def parse_list_page(html: str, selector: str, attribute: str) -> List[str]:
    """Parse a list page to extract URLs."""
    try:
        if not selector:
            return ["Error: No selector provided"]
            
        soup = BeautifulSoup(html, 'html.parser')
        elements = soup.select(selector)
        urls = []
        
        for element in elements:
            if attribute == 'href' and element.name == 'a':
                url = element.get('href')
                if url:
                    urls.append(url)
            elif attribute == 'text':
                urls.append(element.text.strip())
            else:
                attr_value = element.get(attribute)
                if attr_value:
                    urls.append(attr_value)
        
        return urls
    except Exception as e:
        logger.error(f"Error parsing list page: {str(e)}")
        return [f"Error parsing list page: {str(e)}"]


def parse_content_page(html: str, title_selector: str, date_selector: str, body_selector: str) -> Dict[str, str]:
    """Parse a content page to extract title, date, and body."""
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        title = ""
        date = ""
        body = ""
        
        if title_selector:
            title_element = soup.select_one(title_selector)
            title = title_element.text.strip() if title_element else ""
        
        if date_selector:
            date_element = soup.select_one(date_selector)
            date = date_element.text.strip() if date_element else ""
        
        if body_selector:
            body_element = soup.select_one(body_selector)
            body = body_element.text.strip() if body_element else ""
        
        return {
            "title": title,
            "date": date,
            "body": body
        }
    except Exception as e:
        logger.error(f"Error parsing content page: {str(e)}")
        return {"title": "", "date": "", "body": f"Error: {str(e)}"} 