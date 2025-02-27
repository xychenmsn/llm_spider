#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - Playwright Controller

This module provides a controller for browser automation using Playwright.
It allows for headless or headed browser control, page navigation, and script execution.
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

# Import Playwright
try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logging.warning("Playwright not installed. Browser automation will not be available.")

# Set up logging
logger = logging.getLogger(__name__)

class PlaywrightController:
    """
    Controller for browser automation using Playwright.
    
    This class provides methods for browser control, page navigation,
    and script execution for web scraping and testing.
    """
    
    def __init__(self, headless: bool = False, browser_type: str = "chromium"):
        """
        Initialize the PlaywrightController.
        
        Args:
            headless: Whether to run the browser in headless mode
            browser_type: Type of browser to use ('chromium', 'firefox', or 'webkit')
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright is not installed. Please install it with 'pip install playwright' and run 'playwright install'.")
        
        self.headless = headless
        self.browser_type = browser_type
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self._is_running = False
        
        # Load helper scripts
        self.scripts_dir = Path(__file__).parent / "js_scripts"
        self.helper_script = self._load_script("helper.js")
    
    def _load_script(self, script_name: str) -> str:
        """
        Load a JavaScript script from the js_scripts directory.
        
        Args:
            script_name: Name of the script file
            
        Returns:
            The content of the script file
        """
        script_path = self.scripts_dir / script_name
        if not script_path.exists():
            logger.warning(f"Script file {script_name} not found at {script_path}")
            return ""
        
        with open(script_path, "r") as f:
            return f.read()
    
    async def start(self) -> None:
        """
        Start the browser and create a new page.
        """
        if self._is_running:
            logger.warning("Browser is already running")
            return
        
        self.playwright = await async_playwright().start()
        
        # Select browser type
        if self.browser_type == "firefox":
            browser_factory = self.playwright.firefox
        elif self.browser_type == "webkit":
            browser_factory = self.playwright.webkit
        else:
            browser_factory = self.playwright.chromium
        
        # Launch browser
        self.browser = await browser_factory.launch(headless=self.headless)
        
        # Create context and page
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        
        # Initialize helper functions
        if self.helper_script:
            await self.page.add_init_script(self.helper_script)
        
        self._is_running = True
        logger.info(f"Started {self.browser_type} browser (headless={self.headless})")
    
    async def stop(self) -> None:
        """
        Stop the browser and clean up resources.
        """
        if not self._is_running:
            logger.warning("Browser is not running")
            return
        
        if self.page:
            await self.page.close()
            self.page = None
        
        if self.context:
            await self.context.close()
            self.context = None
        
        if self.browser:
            await self.browser.close()
            self.browser = None
        
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
        
        self._is_running = False
        logger.info("Stopped browser")
    
    async def navigate(self, url: str, wait_until: str = "load") -> bool:
        """
        Navigate to a URL.
        
        Args:
            url: URL to navigate to
            wait_until: When to consider navigation complete
                        ('load', 'domcontentloaded', 'networkidle', or 'commit')
                        
        Returns:
            True if navigation was successful, False otherwise
        """
        if not self._is_running:
            logger.warning("Browser is not running")
            return False
        
        try:
            response = await self.page.goto(url, wait_until=wait_until)
            if response and response.ok:
                logger.info(f"Navigated to {url}")
                return True
            else:
                status = response.status if response else "unknown"
                logger.warning(f"Failed to navigate to {url} (status={status})")
                return False
        except Exception as e:
            logger.error(f"Error navigating to {url}: {str(e)}")
            return False
    
    async def execute_script(self, script: str, arg: Any = None) -> Any:
        """
        Execute a JavaScript script in the current page.
        
        Args:
            script: JavaScript code to execute
            arg: Argument to pass to the script
            
        Returns:
            The result of the script execution
        """
        if not self._is_running:
            logger.warning("Browser is not running")
            return None
        
        try:
            result = await self.page.evaluate(script, arg)
            return result
        except Exception as e:
            logger.error(f"Error executing script: {str(e)}")
            return None
    
    async def extract_data(self, selectors: Dict[str, str]) -> Dict[str, Any]:
        """
        Extract data from the current page using CSS selectors.
        
        Args:
            selectors: Dictionary mapping data keys to CSS selectors
            
        Returns:
            Dictionary of extracted data
        """
        if not self._is_running:
            logger.warning("Browser is not running")
            return {}
        
        result = {}
        for key, selector in selectors.items():
            try:
                # Try to get text content
                element = await self.page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    result[key] = text.strip() if text else ""
                else:
                    result[key] = None
            except Exception as e:
                logger.error(f"Error extracting {key} with selector '{selector}': {str(e)}")
                result[key] = None
        
        return result
    
    async def take_screenshot(self, path: str, full_page: bool = True) -> bool:
        """
        Take a screenshot of the current page.
        
        Args:
            path: Path to save the screenshot
            full_page: Whether to capture the full page or just the viewport
            
        Returns:
            True if the screenshot was taken successfully, False otherwise
        """
        if not self._is_running:
            logger.warning("Browser is not running")
            return False
        
        try:
            await self.page.screenshot(path=path, full_page=full_page)
            logger.info(f"Screenshot saved to {path}")
            return True
        except Exception as e:
            logger.error(f"Error taking screenshot: {str(e)}")
            return False
    
    async def wait_for_selector(self, selector: str, timeout: int = 30000) -> bool:
        """
        Wait for an element matching the selector to appear.
        
        Args:
            selector: CSS selector to wait for
            timeout: Maximum time to wait in milliseconds
            
        Returns:
            True if the element appeared, False if timed out
        """
        if not self._is_running:
            logger.warning("Browser is not running")
            return False
        
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception as e:
            logger.error(f"Error waiting for selector '{selector}': {str(e)}")
            return False
    
    async def click(self, selector: str) -> bool:
        """
        Click on an element matching the selector.
        
        Args:
            selector: CSS selector to click
            
        Returns:
            True if the click was successful, False otherwise
        """
        if not self._is_running:
            logger.warning("Browser is not running")
            return False
        
        try:
            await self.page.click(selector)
            return True
        except Exception as e:
            logger.error(f"Error clicking on '{selector}': {str(e)}")
            return False
    
    async def fill(self, selector: str, value: str) -> bool:
        """
        Fill a form field.
        
        Args:
            selector: CSS selector for the form field
            value: Value to fill
            
        Returns:
            True if the field was filled successfully, False otherwise
        """
        if not self._is_running:
            logger.warning("Browser is not running")
            return False
        
        try:
            await self.page.fill(selector, value)
            return True
        except Exception as e:
            logger.error(f"Error filling '{selector}' with '{value}': {str(e)}")
            return False
    
    async def get_html(self) -> str:
        """
        Get the HTML content of the current page.
        
        Returns:
            HTML content as a string
        """
        if not self._is_running:
            logger.warning("Browser is not running")
            return ""
        
        try:
            html = await self.page.content()
            return html
        except Exception as e:
            logger.error(f"Error getting HTML content: {str(e)}")
            return ""
    
    @staticmethod
    async def run_async(coro):
        """
        Run an async coroutine from a synchronous context.
        
        Args:
            coro: Coroutine to run
            
        Returns:
            Result of the coroutine
        """
        return await coro
    
    @classmethod
    def run_sync(cls, coro):
        """
        Run an async coroutine synchronously.
        
        Args:
            coro: Coroutine to run
            
        Returns:
            Result of the coroutine
        """
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)


# Synchronous wrapper for PlaywrightController
class SyncPlaywrightController:
    """
    Synchronous wrapper for PlaywrightController.
    
    This class provides a synchronous interface to the async PlaywrightController.
    """
    
    def __init__(self, headless: bool = False, browser_type: str = "chromium"):
        """
        Initialize the SyncPlaywrightController.
        
        Args:
            headless: Whether to run the browser in headless mode
            browser_type: Type of browser to use ('chromium', 'firefox', or 'webkit')
        """
        self.controller = PlaywrightController(headless=headless, browser_type=browser_type)
    
    def start(self) -> None:
        """Start the browser and create a new page."""
        PlaywrightController.run_sync(self.controller.start())
    
    def stop(self) -> None:
        """Stop the browser and clean up resources."""
        PlaywrightController.run_sync(self.controller.stop())
    
    def navigate(self, url: str, wait_until: str = "load") -> bool:
        """Navigate to a URL."""
        return PlaywrightController.run_sync(self.controller.navigate(url, wait_until))
    
    def execute_script(self, script: str, arg: Any = None) -> Any:
        """Execute a JavaScript script in the current page."""
        return PlaywrightController.run_sync(self.controller.execute_script(script, arg))
    
    def extract_data(self, selectors: Dict[str, str]) -> Dict[str, Any]:
        """Extract data from the current page using CSS selectors."""
        return PlaywrightController.run_sync(self.controller.extract_data(selectors))
    
    def take_screenshot(self, path: str, full_page: bool = True) -> bool:
        """Take a screenshot of the current page."""
        return PlaywrightController.run_sync(self.controller.take_screenshot(path, full_page))
    
    def wait_for_selector(self, selector: str, timeout: int = 30000) -> bool:
        """Wait for an element matching the selector to appear."""
        return PlaywrightController.run_sync(self.controller.wait_for_selector(selector, timeout))
    
    def click(self, selector: str) -> bool:
        """Click on an element matching the selector."""
        return PlaywrightController.run_sync(self.controller.click(selector))
    
    def fill(self, selector: str, value: str) -> bool:
        """Fill a form field."""
        return PlaywrightController.run_sync(self.controller.fill(selector, value))
    
    def get_html(self) -> str:
        """Get the HTML content of the current page."""
        return PlaywrightController.run_sync(self.controller.get_html()) 