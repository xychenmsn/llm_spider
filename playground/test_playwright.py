#!/usr/bin/env python3
"""
Test script for the PlaywrightController.

This script demonstrates how to use the PlaywrightController to automate browser interactions.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the project root to the path so we can import from the project
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from utils.playwright_controller import PlaywrightController, SyncPlaywrightController

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
        title = await controller.execute_script("return document.title")
        print(f"Page title: {title}")
        
        # Take a screenshot
        screenshot_path = os.path.join(project_root, "playground", "screenshot.png")
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
        title = controller.execute_script("return document.title")
        print(f"Page title: {title}")
        
        # Take a screenshot
        screenshot_path = os.path.join(project_root, "playground", "screenshot_sync.png")
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
    # Test the async controller
    asyncio.run(test_async_playwright())
    
    # Test the sync controller
    test_sync_playwright() 