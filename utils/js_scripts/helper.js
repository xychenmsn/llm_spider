/**
 * LLM Spider - Browser Automation Helper Functions
 * 
 * This script provides helper functions for browser automation and data extraction.
 * It is injected into the browser context by the PlaywrightController.
 */

// Global namespace for LLM Spider functions
window.LLMSpider = window.LLMSpider || {};

/**
 * Extract text content from an element
 * @param {string} selector - CSS selector
 * @returns {string|null} - Text content or null if element not found
 */
LLMSpider.getText = (selector) => {
    const element = document.querySelector(selector);
    return element ? element.textContent.trim() : null;
};

/**
 * Extract attribute value from an element
 * @param {string} selector - CSS selector
 * @param {string} attribute - Attribute name
 * @returns {string|null} - Attribute value or null if element not found
 */
LLMSpider.getAttribute = (selector, attribute) => {
    const element = document.querySelector(selector);
    return element ? element.getAttribute(attribute) : null;
};

/**
 * Extract multiple elements matching a selector
 * @param {string} selector - CSS selector
 * @param {function} extractor - Function to extract data from each element
 * @returns {Array} - Array of extracted data
 */
LLMSpider.getAll = (selector, extractor) => {
    const elements = Array.from(document.querySelectorAll(selector));
    return elements.map(extractor);
};

/**
 * Extract text content from multiple elements
 * @param {string} selector - CSS selector
 * @returns {Array<string>} - Array of text content
 */
LLMSpider.getAllText = (selector) => {
    return LLMSpider.getAll(selector, el => el.textContent.trim());
};

/**
 * Extract attribute values from multiple elements
 * @param {string} selector - CSS selector
 * @param {string} attribute - Attribute name
 * @returns {Array<string>} - Array of attribute values
 */
LLMSpider.getAllAttributes = (selector, attribute) => {
    return LLMSpider.getAll(selector, el => el.getAttribute(attribute));
};

/**
 * Extract data from a table
 * @param {string} tableSelector - CSS selector for the table
 * @param {boolean} hasHeader - Whether the table has a header row
 * @returns {Object} - Table data with headers and rows
 */
LLMSpider.extractTable = (tableSelector, hasHeader = true) => {
    const table = document.querySelector(tableSelector);
    if (!table) return { headers: [], rows: [] };
    
    const rows = Array.from(table.querySelectorAll('tr'));
    if (rows.length === 0) return { headers: [], rows: [] };
    
    let headers = [];
    let startIndex = 0;
    
    if (hasHeader) {
        startIndex = 1;
        headers = Array.from(rows[0].querySelectorAll('th, td')).map(cell => cell.textContent.trim());
    }
    
    const dataRows = [];
    for (let i = startIndex; i < rows.length; i++) {
        const cells = Array.from(rows[i].querySelectorAll('td')).map(cell => cell.textContent.trim());
        dataRows.push(cells);
    }
    
    return {
        headers,
        rows: dataRows
    };
};

/**
 * Extract structured data from the page
 * @param {Object} selectors - Object mapping data keys to CSS selectors
 * @returns {Object} - Extracted data
 */
LLMSpider.extractData = (selectors) => {
    const result = {};
    
    for (const [key, selector] of Object.entries(selectors)) {
        result[key] = LLMSpider.getText(selector);
    }
    
    return result;
};

/**
 * Extract metadata from the page (title, description, etc.)
 * @returns {Object} - Page metadata
 */
LLMSpider.extractMetadata = () => {
    return {
        title: document.title,
        url: window.location.href,
        description: LLMSpider.getText('meta[name="description"]') || '',
        keywords: LLMSpider.getText('meta[name="keywords"]') || '',
        canonical: LLMSpider.getAttribute('link[rel="canonical"]', 'href') || window.location.href,
        ogTitle: LLMSpider.getAttribute('meta[property="og:title"]', 'content') || '',
        ogDescription: LLMSpider.getAttribute('meta[property="og:description"]', 'content') || '',
        ogImage: LLMSpider.getAttribute('meta[property="og:image"]', 'content') || ''
    };
};

/**
 * Scroll to the bottom of the page
 * @param {number} delay - Delay between scroll steps in milliseconds
 * @param {number} step - Scroll step size in pixels
 * @returns {Promise} - Promise that resolves when scrolling is complete
 */
LLMSpider.scrollToBottom = async (delay = 100, step = 300) => {
    const getScrollHeight = () => document.documentElement.scrollHeight;
    const getScrollTop = () => document.documentElement.scrollTop;
    const getClientHeight = () => document.documentElement.clientHeight;
    
    let lastScrollHeight = getScrollHeight();
    let scrollAttempts = 0;
    const maxScrollAttempts = 100; // Prevent infinite scrolling
    
    while (scrollAttempts < maxScrollAttempts) {
        window.scrollBy(0, step);
        await new Promise(resolve => setTimeout(resolve, delay));
        
        const scrollTop = getScrollTop();
        const clientHeight = getClientHeight();
        const scrollHeight = getScrollHeight();
        
        // Check if we've reached the bottom
        if (scrollTop + clientHeight >= scrollHeight) {
            // Wait a bit more to see if more content loads
            await new Promise(resolve => setTimeout(resolve, delay * 5));
            
            // Check if the scroll height has changed (infinite scroll)
            if (scrollHeight === lastScrollHeight) {
                break;
            }
            
            lastScrollHeight = scrollHeight;
        }
        
        scrollAttempts++;
    }
    
    return true;
};

/**
 * Wait for an element to appear in the DOM
 * @param {string} selector - CSS selector
 * @param {number} timeout - Maximum time to wait in milliseconds
 * @returns {Promise<Element|null>} - Promise that resolves with the element or null if timed out
 */
LLMSpider.waitForElement = async (selector, timeout = 5000) => {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeout) {
        const element = document.querySelector(selector);
        if (element) return element;
        await new Promise(resolve => setTimeout(resolve, 100));
    }
    
    return null;
};

/**
 * Click an element
 * @param {string} selector - CSS selector
 * @returns {boolean} - Whether the click was successful
 */
LLMSpider.click = (selector) => {
    const element = document.querySelector(selector);
    if (!element) return false;
    
    element.click();
    return true;
};

/**
 * Fill a form field
 * @param {string} selector - CSS selector
 * @param {string} value - Value to fill
 * @returns {boolean} - Whether the fill was successful
 */
LLMSpider.fill = (selector, value) => {
    const element = document.querySelector(selector);
    if (!element) return false;
    
    element.value = value;
    element.dispatchEvent(new Event('input', { bubbles: true }));
    element.dispatchEvent(new Event('change', { bubbles: true }));
    return true;
};

/**
 * Submit a form
 * @param {string} selector - CSS selector for the form
 * @returns {boolean} - Whether the submission was successful
 */
LLMSpider.submitForm = (selector) => {
    const form = document.querySelector(selector);
    if (!form) return false;
    
    form.submit();
    return true;
};

/**
 * Extract links from the page
 * @param {string} selector - CSS selector for links (default: all links)
 * @returns {Array<Object>} - Array of link objects with href, text, and title
 */
LLMSpider.extractLinks = (selector = 'a') => {
    return LLMSpider.getAll(selector, link => ({
        href: link.href,
        text: link.textContent.trim(),
        title: link.getAttribute('title') || ''
    }));
};

/**
 * Extract images from the page
 * @param {string} selector - CSS selector for images (default: all images)
 * @returns {Array<Object>} - Array of image objects with src, alt, and title
 */
LLMSpider.extractImages = (selector = 'img') => {
    return LLMSpider.getAll(selector, img => ({
        src: img.src,
        alt: img.getAttribute('alt') || '',
        title: img.getAttribute('title') || ''
    }));
};

// Export the LLMSpider object
console.log('LLM Spider helper functions loaded'); 