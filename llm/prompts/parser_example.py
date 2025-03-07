#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Example parser code for the LLM Spider.
This file contains example code that will be used as a prompt for the LLM.
"""

def parse_webpage(url):
    """
    Universal parser that determines page type and extracts relevant information.
    
    Args:
        url (str): URL of the webpage to parse
        
    Returns:
        dict: JSON-compatible dictionary containing parsed data
    """
    # Fetch HTML content
    try:
        import requests
        from bs4 import BeautifulSoup
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Determine page type
        is_article_list = _is_article_list_page(soup)
        
        # Parse according to page type
        if is_article_list:
            result = _parse_article_list(soup, url)
            result['page_type'] = 'article_list'
        else:
            result = _parse_article(soup, url)
            result['page_type'] = 'article'
            
        result['url'] = url
        return result
        
    except Exception as e:
        return {
            'error': str(e),
            'url': url,
            'success': False
        }


def _is_article_list_page(soup):
    """
    Determine if the page is an article list page.
    
    Args:
        soup (BeautifulSoup): Parsed HTML
        
    Returns:
        bool: True if page is an article list, False otherwise
    """
    # Check for multiple article elements
    article_elements = soup.select('article, .article, .post, .entry')
    if len(article_elements) > 3:
        return True
        
    # Check for list of links with dates
    link_date_pairs = 0
    for link in soup.find_all('a', href=True):
        date_nearby = link.find_next(text=lambda text: _looks_like_date(text))
        if date_nearby and date_nearby.parent.get_text().strip() != '':
            link_date_pairs += 1
    
    if link_date_pairs > 3:
        return True
        
    # Check for pagination
    pagination = soup.select('.pagination, .pager, .pages, nav[role="navigation"]')
    if pagination and len(article_elements) > 0:
        return True
        
    return False


def _looks_like_date(text):
    """Check if text resembles a date format"""
    if not text:
        return False
    import re
    date_patterns = [
        r'\d{1,2}/\d{1,2}/\d{2,4}',  # MM/DD/YYYY
        r'\d{4}-\d{1,2}-\d{1,2}',     # YYYY-MM-DD
        r'[A-Za-z]{3,9} \d{1,2},? \d{4}',  # Month DD, YYYY
        r'\d{1,2} [A-Za-z]{3,9},? \d{4}'   # DD Month YYYY
    ]
    return any(re.search(pattern, text) for pattern in date_patterns)


def _parse_article_list(soup, base_url):
    """
    Parse an article list page.
    
    Args:
        soup (BeautifulSoup): Parsed HTML
        base_url (str): Base URL for resolving relative links
        
    Returns:
        dict: Parsed article list data
    """
    articles = []
    
    # Try different selectors for article containers
    article_containers = (
        soup.select('article, .article, .post, .entry, .item') or
        soup.select('.news-item, .blog-post, .search-result') or
        soup.select('li:has(a):has(time), div:has(a):has(h2)')
    )
    
    from urllib.parse import urljoin
    
    for container in article_containers:
        # Extract title and link
        title_elem = container.select_one('h1, h2, h3, .title, .headline')
        link_elem = container.select_one('a') or (title_elem.select_one('a') if title_elem else None)
        
        # Extract date
        date_elem = container.select_one('time, .date, .time, .published, .datetime')
        
        # Extract preview
        preview_elem = container.select_one('.summary, .excerpt, .description, .preview, p')
        
        # Only include if we have at least a title or link
        if (title_elem or link_elem):
            article = {}
            
            if title_elem:
                article['title'] = title_elem.get_text().strip()
            
            if link_elem and 'href' in link_elem.attrs:
                article['url'] = urljoin(base_url, link_elem['href'])
            
            if date_elem:
                article['date'] = date_elem.get_text().strip()
            
            if preview_elem and preview_elem != title_elem:
                article['preview'] = preview_elem.get_text().strip()
                
            articles.append(article)
    
    return {'articles': articles}


def _parse_article(soup, url):
    """
    Parse a single article page.
    
    Args:
        soup (BeautifulSoup): Parsed HTML
        url (str): URL of the article
        
    Returns:
        dict: Parsed article data
    """
    # Extract title
    title_candidates = [
        soup.select_one('h1'),
        soup.select_one('header h1, header h2'),
        soup.select_one('.post-title, .entry-title, .article-title'),
        soup.select_one('meta[property="og:title"]')
    ]
    title = next((t.get_text().strip() if not t.has_attr('content') else t['content'] 
                  for t in title_candidates if t), None)
    
    # Extract author
    author_candidates = [
        soup.select_one('.author, .byline, .writer'),
        soup.select_one('meta[name="author"]'),
        soup.select_one('[rel="author"]'),
        soup.select_one('[itemprop="author"]')
    ]
    author = next((a.get_text().strip() if not a.has_attr('content') else a['content'] 
                   for a in author_candidates if a), None)
    
    # Extract date
    date_candidates = [
        soup.select_one('time, .date, .published, [itemprop="datePublished"]'),
        soup.select_one('meta[property="article:published_time"]')
    ]
    date = next((d.get_text().strip() if not d.has_attr('content') else d['content'] 
                 for d in date_candidates if d), None)
    
    # Extract content
    content_candidates = [
        soup.select_one('article, [itemprop="articleBody"]'),
        soup.select_one('.post-content, .entry-content, .article-content, .content'),
        soup.select_one('main'),
        soup.select_one('#content, #main')
    ]
    
    content_element = next((c for c in content_candidates if c), None)
    
    # Process content if found
    if content_element:
        # Remove unwanted elements
        for selector in [
            '.ad, .advertisement, .banner', 
            '.sidebar, .widget, .related',
            'nav, footer, .footer, .nav',
            '.social, .sharing, .share',
            '.comments, #comments',
            'script, style, iframe'
        ]:
            for el in content_element.select(selector):
                el.decompose()
    
    # Extract the cleaned text
    content_text = content_element.get_text(separator=' ', strip=True) if content_element else None
    
    return {
        'title': title,
        'author': author,
        'date': date,
        'content': content_text,
        'url': url
    } 