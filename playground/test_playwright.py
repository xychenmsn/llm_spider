#!/usr/bin/env python3
"""
Test script for the PlaywrightController.

This script demonstrates how to use the PlaywrightController to automate browser interactions.
"""

import os
import sys
import asyncio
import datetime
import uuid
from pathlib import Path

# Add the project root to the path so we can import from the project
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from utils.playwright_controller import PlaywrightController, SyncPlaywrightController

def generate_filename(prefix="screenshot"):
    """Generate a unique filename with timestamp and random string."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    random_str = str(uuid.uuid4())[:8]  # Use first 8 chars of UUID
    return f"{prefix}_{timestamp}_{random_str}.png"

async def test_async_playwright():
    """Test the async PlaywrightController."""
    print("Testing async PlaywrightController...")
    
    # Create a controller with a visible browser
    controller = PlaywrightController(headless=False)
    
    try:
        # Start the browser
        await controller.start()
        print("Browser started")
        
        # Navigate to a URL
        url = "https://example.com"
        success = await controller.navigate(url)
        print(f"Navigation to {url}: {'Success' if success else 'Failed'}")
        
        # Extract data using selectors
        data = await controller.extract_data({
            "title": "h1",
            "description": "p"
        })
        print(f"Extracted data: {data}")
        
        # Execute a script to get the page title
        # For Playwright's evaluate, use a function format instead of a return statement
        title = await controller.execute_script("() => document.title")
        print(f"Page title: {title}")
        
        # Take a screenshot
        screenshots_dir = os.path.join(project_root, "tmp", "screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)  # Ensure directory exists
        screenshot_filename = generate_filename("async")
        screenshot_path = os.path.join(screenshots_dir, screenshot_filename)
        await controller.take_screenshot(screenshot_path)
        print(f"Screenshot saved to {screenshot_path}")
        
        # Get the HTML content
        html = await controller.get_html()
        print(f"HTML content length: {len(html)} characters")
        
        # Wait for user to see the browser
        print("Waiting for 3 seconds...")
        await asyncio.sleep(3)
        
    finally:
        # Stop the browser
        await controller.stop()
        print("Browser stopped")

def test_sync_playwright():
    """Test the synchronous PlaywrightController wrapper."""
    print("\nTesting synchronous PlaywrightController...")
    
    # Create a controller with a visible browser
    controller = SyncPlaywrightController(headless=False)
    
    try:
        # Start the browser
        controller.start()
        print("Browser started")
        
        # Navigate to a URL
        url = "https://example.com"
        success = controller.navigate(url)
        print(f"Navigation to {url}: {'Success' if success else 'Failed'}")
        
        # Extract data using selectors
        data = controller.extract_data({
            "title": "h1",
            "description": "p"
        })
        print(f"Extracted data: {data}")
        
        # Execute a script to get the page title
        # For Playwright's evaluate, use a function format instead of a return statement
        title = controller.execute_script("() => document.title")
        print(f"Page title: {title}")
        
        # Take a screenshot
        screenshots_dir = os.path.join(project_root, "tmp", "screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)  # Ensure directory exists
        screenshot_filename = generate_filename("sync")
        screenshot_path = os.path.join(screenshots_dir, screenshot_filename)
        controller.take_screenshot(screenshot_path)
        print(f"Screenshot saved to {screenshot_path}")
        
        # Wait for user to see the browser
        print("Waiting for 3 seconds...")
        import time
        time.sleep(3)
        
    finally:
        # Stop the browser
        controller.stop()
        print("Browser stopped")

if __name__ == "__main__":
    # Run tests in the correct order to avoid event loop issues
    # First run the sync test (which creates its own event loop)
    test_sync_playwright()
    
    # Then run the async test
    asyncio.run(test_async_playwright()) 