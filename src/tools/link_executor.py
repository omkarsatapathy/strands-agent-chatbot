"""URL content fetcher tool for the Researcher Agent.

This tool fetches URL content, extracts metadata, and parses page content
with comprehensive error handling and fallback mechanisms.
"""
import requests
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import re
from ..logging_config import get_logger
from strands import tool

logger = get_logger("chatbot.tools.link_executor")

# Common user agents for rotation
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]


def _get_headers(user_agent_index: int = 0) -> Dict[str, str]:
    """Get request headers with rotating user agent."""
    return {
        'User-Agent': USER_AGENTS[user_agent_index % len(USER_AGENTS)],
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }


def _extract_metadata(soup: BeautifulSoup, url: str) -> Dict[str, Any]:
    """Extract metadata from the page including Open Graph, Twitter cards, and standard meta tags."""
    metadata = {
        'title': None,
        'description': None,
        'author': None,
        'published_date': None,
        'modified_date': None,
        'keywords': [],
        'og': {},
        'twitter': {},
        'canonical_url': None,
        'language': None,
        'site_name': None,
    }

    # Extract title
    if soup.title:
        metadata['title'] = soup.title.string.strip() if soup.title.string else None

    # Extract Open Graph and Twitter meta tags
    og_title = soup.find('meta', property='og:title')
    if og_title and og_title.get('content'):
        metadata['og']['title'] = og_title['content']
        if not metadata['title']:
            metadata['title'] = og_title['content']

    og_description = soup.find('meta', property='og:description')
    if og_description and og_description.get('content'):
        metadata['og']['description'] = og_description['content']

    og_image = soup.find('meta', property='og:image')
    if og_image and og_image.get('content'):
        metadata['og']['image'] = og_image['content']

    og_site_name = soup.find('meta', property='og:site_name')
    if og_site_name and og_site_name.get('content'):
        metadata['site_name'] = og_site_name['content']

    og_type = soup.find('meta', property='og:type')
    if og_type and og_type.get('content'):
        metadata['og']['type'] = og_type['content']

    # Twitter card metadata
    twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
    if twitter_title and twitter_title.get('content'):
        metadata['twitter']['title'] = twitter_title['content']

    twitter_description = soup.find('meta', attrs={'name': 'twitter:description'})
    if twitter_description and twitter_description.get('content'):
        metadata['twitter']['description'] = twitter_description['content']

    twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
    if twitter_image and twitter_image.get('content'):
        metadata['twitter']['image'] = twitter_image['content']

    # Standard meta description
    description = soup.find('meta', attrs={'name': 'description'})
    if description and description.get('content'):
        metadata['description'] = description['content']
    elif metadata['og'].get('description'):
        metadata['description'] = metadata['og']['description']

    # Author
    author = soup.find('meta', attrs={'name': 'author'})
    if author and author.get('content'):
        metadata['author'] = author['content']

    # Keywords
    keywords = soup.find('meta', attrs={'name': 'keywords'})
    if keywords and keywords.get('content'):
        metadata['keywords'] = [k.strip() for k in keywords['content'].split(',')]

    # Published/Modified dates
    for date_prop in ['article:published_time', 'datePublished', 'pubdate']:
        date_tag = soup.find('meta', property=date_prop) or soup.find('meta', attrs={'name': date_prop})
        if date_tag and date_tag.get('content'):
            metadata['published_date'] = date_tag['content']
            break

    for date_prop in ['article:modified_time', 'dateModified']:
        date_tag = soup.find('meta', property=date_prop) or soup.find('meta', attrs={'name': date_prop})
        if date_tag and date_tag.get('content'):
            metadata['modified_date'] = date_tag['content']
            break

    # Canonical URL
    canonical = soup.find('link', rel='canonical')
    if canonical and canonical.get('href'):
        metadata['canonical_url'] = canonical['href']

    # Language
    html_tag = soup.find('html')
    if html_tag and html_tag.get('lang'):
        metadata['language'] = html_tag['lang']

    return metadata


def _extract_main_content(soup: BeautifulSoup) -> str:
    """Extract the main content from the page with smart content detection."""
    # Try to find main content containers
    main_selectors = [
        ('article', {}),
        ('main', {}),
        ('div', {'class': re.compile(r'(article|content|post|entry|main)', re.I)}),
        ('div', {'id': re.compile(r'(article|content|post|entry|main)', re.I)}),
        ('div', {'role': 'main'}),
    ]

    main_content = None
    for tag, attrs in main_selectors:
        main_content = soup.find(tag, attrs)
        if main_content:
            break

    # Fall back to body if no main content found
    if not main_content:
        main_content = soup.body if soup.body else soup

    # Create a copy to avoid modifying original
    content_soup = BeautifulSoup(str(main_content), 'html.parser')

    # Remove unwanted elements
    unwanted_tags = [
        'script', 'style', 'nav', 'footer', 'header', 'aside',
        'form', 'button', 'iframe', 'noscript', 'svg', 'canvas',
        'advertisement', 'ads', 'social-share', 'comments'
    ]
    for tag in unwanted_tags:
        for element in content_soup.find_all(tag):
            element.decompose()

    # Remove elements with common ad/nav class patterns
    ad_patterns = re.compile(
        r'(ad-|ads-|advert|banner|sidebar|widget|popup|modal|cookie|newsletter|'
        r'social|share|comment|related|recommend|footer|header|nav|menu)',
        re.I
    )

    for element in content_soup.find_all(class_=ad_patterns):
        element.decompose()

    for element in content_soup.find_all(id=ad_patterns):
        element.decompose()

    return content_soup


def _clean_text(text: str) -> str:
    """Clean and normalize extracted text."""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split('\n')]
    # Remove empty lines and join
    text = '\n'.join(line for line in lines if line)
    return text.strip()


def _extract_links(soup: BeautifulSoup, base_url: str) -> list:
    """Extract relevant links from the page."""
    links = []
    seen_urls = set()

    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        text = a_tag.get_text(strip=True)

        # Skip empty or javascript links
        if not href or href.startswith(('javascript:', '#', 'mailto:', 'tel:')):
            continue

        # Make absolute URL
        absolute_url = urljoin(base_url, href)

        # Skip duplicates and very long URLs
        if absolute_url in seen_urls or len(absolute_url) > 500:
            continue

        seen_urls.add(absolute_url)

        if text and len(text) > 3:
            links.append({
                'url': absolute_url,
                'text': text[:200]  # Limit text length
            })

    return links[:20]  # Return top 20 links


def _fetch_url_content_impl(url: str, max_content_length: int = 8000, include_links: bool = False) -> Dict[str, Any]:
    """Internal implementation for URL content fetching."""
    logger.info(f"Fetching URL content", extra={"extra_data": {"url": url}})

    result = {
        'url': url,
        'status': 'error',
        'metadata': {},
        'content': '',
        'links': [],
        'error': None
    }

    # Validate URL
    try:
        parsed = urlparse(url)
        if not parsed.scheme:
            url = 'https://' + url
            parsed = urlparse(url)

        if parsed.scheme not in ('http', 'https'):
            result['error'] = f"Invalid URL scheme: {parsed.scheme}. Only HTTP/HTTPS supported."
            return result

        if not parsed.netloc:
            result['error'] = "Invalid URL: No domain specified"
            return result

    except Exception as e:
        result['error'] = f"Invalid URL format: {str(e)}"
        return result

    # Try fetching with retries and user agent rotation
    response = None
    last_error = None

    for attempt in range(3):
        try:
            headers = _get_headers(attempt)

            logger.debug(
                f"Fetch attempt {attempt + 1}/3",
                extra={"extra_data": {"url": url, "user_agent_index": attempt}}
            )

            response = requests.get(
                url,
                headers=headers,
                timeout=15,
                allow_redirects=True,
                verify=True
            )

            # Check for successful response
            if response.status_code == 200:
                break
            elif response.status_code in (403, 429):
                # Forbidden or rate limited, try different user agent
                last_error = f"HTTP {response.status_code}"
                continue
            else:
                response.raise_for_status()

        except requests.exceptions.Timeout:
            last_error = "Request timed out"
            logger.warning(f"Timeout on attempt {attempt + 1}", extra={"extra_data": {"url": url}})
            continue
        except requests.exceptions.SSLError:
            # Try without SSL verification as fallback
            try:
                response = requests.get(url, headers=_get_headers(attempt), timeout=15, verify=False)
                if response.status_code == 200:
                    logger.warning("SSL verification disabled for this request", extra={"extra_data": {"url": url}})
                    break
            except Exception as ssl_fallback_error:
                last_error = f"SSL error: {str(ssl_fallback_error)}"
            continue
        except requests.exceptions.ConnectionError as e:
            last_error = f"Connection error: {str(e)}"
            continue
        except requests.exceptions.HTTPError as e:
            last_error = f"HTTP error: {e.response.status_code}"
            continue
        except Exception as e:
            last_error = f"Request failed: {str(e)}"
            continue

    if not response or response.status_code != 200:
        result['error'] = last_error or "Failed to fetch URL after 3 attempts"
        logger.error(f"Failed to fetch URL", extra={"extra_data": {"url": url, "error": result['error']}})
        return result

    # Parse content
    try:
        # Detect encoding
        encoding = response.encoding
        if not encoding or encoding == 'ISO-8859-1':
            # Try to detect from content
            encoding = response.apparent_encoding or 'utf-8'

        content = response.content.decode(encoding, errors='replace')
        soup = BeautifulSoup(content, 'html.parser')

        # Extract metadata
        result['metadata'] = _extract_metadata(soup, url)

        # Extract main content
        content_soup = _extract_main_content(soup)
        text_content = content_soup.get_text(separator='\n', strip=True)
        text_content = _clean_text(text_content)

        # Truncate if needed
        if len(text_content) > max_content_length:
            text_content = text_content[:max_content_length] + "... [content truncated]"

        result['content'] = text_content

        # Extract links if requested
        if include_links:
            result['links'] = _extract_links(soup, url)

        result['status'] = 'success'

        logger.info(
            f"Successfully fetched URL content",
            extra={"extra_data": {
                "url": url,
                "title": result['metadata'].get('title'),
                "content_length": len(result['content']),
                "links_count": len(result['links'])
            }}
        )

    except Exception as e:
        result['error'] = f"Failed to parse content: {str(e)}"
        logger.error(f"Parse error", extra={"extra_data": {"url": url, "error": str(e)}}, exc_info=True)

    return result


@tool
def fetch_url_content(url: str, max_content_length: int = 8000, include_links: bool = False) -> str:
    """
    Strands tool: Fetch and parse content from a URL with metadata extraction.

    This tool fetches a webpage, extracts metadata (title, description, Open Graph, etc.),
    and parses the main content. It includes comprehensive error handling and fallback mechanisms.

    Args:
        url: The URL to fetch content from
        max_content_length: Maximum characters of content to return (default: 8000)
        include_links: Whether to include extracted links from the page (default: False)

    Returns:
        JSON string containing URL content, metadata, and status
    """
    import json
    result = _fetch_url_content_impl(url, max_content_length, include_links)
    # Return as JSON string to avoid strands dict content bug
    return json.dumps(result, ensure_ascii=False)


@tool
def fetch_multiple_urls(urls: list, max_content_length: int = 5000) -> str:
    """
    Strands tool: Fetch content from multiple URLs in sequence.

    This tool fetches and parses content from a list of URLs, useful for
    comparing information across multiple sources.

    Args:
        urls: List of URLs to fetch (maximum 5)
        max_content_length: Maximum characters per URL content (default: 5000)

    Returns:
        JSON string containing results for all URLs
    """
    import json
    logger.info(f"Fetching multiple URLs", extra={"extra_data": {"url_count": len(urls)}})

    # Limit to 5 URLs to prevent abuse
    urls = urls[:5]

    results = []
    success_count = 0
    failed_count = 0

    for url in urls:
        # Call the underlying function directly (not the tool wrapper)
        result = _fetch_url_content_impl(
            url=url,
            max_content_length=max_content_length,
            include_links=False
        )

        results.append(result)

        if result.get('status') == 'success':
            success_count += 1
        else:
            failed_count += 1

    # Return as JSON string to avoid strands dict content bug
    return json.dumps({
        'results': results,
        'success_count': success_count,
        'failed_count': failed_count,
        'total': len(urls)
    }, ensure_ascii=False)