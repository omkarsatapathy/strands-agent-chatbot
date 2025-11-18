"""Custom Strands tools for the chatbot agent."""
import requests
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from ..config import Config
from ..logging_config import get_logger
from strands import tool

logger = get_logger("chatbot.tools")

@tool
def google_search_with_context(query: str) -> Dict[str, Any]:
    """
    Strands tool: Perform a Google Custom Search and return the top result with full page context.

    This tool searches Google and fetches the full content of the top result article.
    Set top_k=1 to return only the most relevant result.

    Args:
        query: The search query string

    Returns:
        Dictionary with the top search result including title, link, snippet, and full page context
    """
    api_key, search_engine_id = Config.get_google_credentials()

    logger.info(
        f"Starting Google web search with context",
        extra={"extra_data": {"query": query, "top_k": 1}}
    )

    api_url = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={search_engine_id}"

    try:
        logger.debug(
            f"Sending request to Google Custom Search API",
            extra={"extra_data": {"api_url": api_url.replace(api_key, "***")}}
        )

        response = requests.get(api_url, params={
            'q': query,
            'num': 3  # top_k = 1
        })

        logger.debug(
            f"Received response from Google API",
            extra={"extra_data": {"status_code": response.status_code}}
        )

        response.raise_for_status()
    
        data = response.json()

        logger.debug(
            f"Raw API response",
            extra={"extra_data": {"response_keys": list(data.keys())}}
        )

        if 'items' in data and len(data['items']) > 0:
            item = data['items'][0]  # Get only the top result

            result = {
                'title': item.get('title', ''),
                'link': item.get('link', ''),
                'snippet': item.get('snippet', ''),
                'displayLink': item.get('displayLink', ''),
                'formattedUrl': item.get('formattedUrl', '')
            }

            # Fetch full page context
            page_context = _fetch_page_context(result['link'])
            result['page_context'] = page_context

            logger.debug(
                f"Processed top search result",
                extra={"extra_data": {"title": result['title'], "link": result['link'], "context_length": len(page_context)}}
            )

            logger.info(
                f"Google web search with context completed",
                extra={"extra_data": {"query": query, "url": result['link']}}
            )

            return result
        else:
            logger.warning(
                f"No search results found",
                extra={"extra_data": {"query": query}}
            )
            return {"error": "No search results found"}

    except requests.exceptions.HTTPError as e:
        logger.error(
            f"HTTP error during Google search",
            extra={"extra_data": {"status_code": e.response.status_code, "query": query}},
            exc_info=True
        )
        return {"error": f"Search failed with HTTP {e.response.status_code}: {str(e)}"}
    except Exception as e:
        logger.error(
            f"Unexpected error during Google search",
            extra={"extra_data": {"query": query, "error": str(e)}},
            exc_info=True
        )
        return {"error": f"Search failed: {str(e)}"}


def _fetch_page_context(url: str, max_chars: int = 5000) -> str:
    """
    Fetch and extract the main text content from a webpage.

    Args:
        url: The URL to fetch
        max_chars: Maximum characters to return (default: 5000)

    Returns:
        Extracted text content from the page
    """
    try:
        logger.debug(
            f"Fetching page content",
            extra={"extra_data": {"url": url}}
        )

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()

        # Get text content
        text = soup.get_text(separator=' ', strip=True)

        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)

        # Truncate to max_chars
        if len(text) > max_chars:
            text = text[:max_chars] + "..."

        logger.debug(
            f"Successfully fetched page content",
            extra={"extra_data": {"url": url, "text_length": len(text)}}
        )

        return text

    except requests.exceptions.Timeout:
        logger.warning(
            f"Timeout fetching page content",
            extra={"extra_data": {"url": url}}
        )
        return "Error: Page fetch timeout"
    except requests.exceptions.HTTPError as e:
        logger.warning(
            f"HTTP error fetching page content",
            extra={"extra_data": {"url": url, "status_code": e.response.status_code}}
        )
        return f"Error: HTTP {e.response.status_code}"
    except Exception as e:
        logger.warning(
            f"Error fetching page content",
            extra={"extra_data": {"url": url, "error": str(e)}}
        )
        return f"Error fetching page: {str(e)}"
