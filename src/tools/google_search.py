"""Custom tools for the chatbot agent."""
import requests
from typing import List, Dict, Any
from ..config import Config
from ..logging_config import get_logger

logger = get_logger("chatbot.tools")


def google_search(query: str, num_results: int = 5) -> List[Dict[str, Any]]:
    """
    Perform a Google Custom Search and return results.

    Args:
        query: The search query string
        num_results: Number of results to return (default: 5)

    Returns:
        List of search results with titles, links, and snippets
    """
    api_key, search_engine_id = Config.get_google_credentials()

    logger.info(
        f"Starting Google web search",
        extra={"extra_data": {"query": query, "num_results": num_results}}
    )

    api_url = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={search_engine_id}"

    try:
        logger.debug(
            f"Sending request to Google Custom Search API",
            extra={"extra_data": {"api_url": api_url.replace(api_key, "***")}}
        )

        response = requests.get(api_url, params={
            'q': query,
            'num': num_results
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

        results = []
        if 'items' in data:
            for idx, item in enumerate(data['items']):
                result = {
                    'title': item.get('title', ''),
                    'link': item.get('link', ''),
                    'snippet': item.get('snippet', ''),
                    'displayLink': item.get('displayLink', ''),
                    'formattedUrl': item.get('formattedUrl', '')
                }

                # Add metadata if available
                if 'pagemap' in item:
                    result['metadata'] = item['pagemap']

                results.append(result)

                logger.debug(
                    f"Processed search result {idx + 1}",
                    extra={"extra_data": {"title": result['title'], "link": result['link']}}
                )

        logger.info(
            f"Google web search completed",
            extra={"extra_data": {"results_found": len(results), "query": query}}
        )

        return results
    except requests.exceptions.HTTPError as e:
        logger.error(
            f"HTTP error during Google search",
            extra={"extra_data": {"status_code": e.response.status_code, "query": query}},
            exc_info=True
        )
        return [{"error": f"Search failed with HTTP {e.response.status_code}: {str(e)}"}]
    except Exception as e:
        logger.error(
            f"Unexpected error during Google search",
            extra={"extra_data": {"query": query, "error": str(e)}},
            exc_info=True
        )
        return [{"error": f"Search failed: {str(e)}"}]


def google_image_search(query: str, num_results: int = 5) -> List[Dict[str, Any]]:
    """
    Perform a Google Image Search and return results.

    Args:
        query: The search query string
        num_results: Number of image results to return (default: 5)

    Returns:
        List of image search results with links
    """
    api_key, search_engine_id = Config.get_google_credentials()

    logger.info(
        f"Starting Google image search",
        extra={"extra_data": {"query": query, "num_results": num_results}}
    )

    api_url = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={search_engine_id}"

    try:
        logger.debug(
            f"Sending image search request to Google API",
            extra={"extra_data": {"api_url": api_url.replace(api_key, "***")}}
        )

        response = requests.get(api_url, params={
            'q': query,
            'num': num_results,
            'search_type': 'image'
        })

        logger.debug(
            f"Received image search response",
            extra={"extra_data": {"status_code": response.status_code}}
        )

        response.raise_for_status()
        data = response.json()

        logger.debug(
            f"Raw image search API response",
            extra={"extra_data": {"response_keys": list(data.keys())}}
        )

        results = []
        if 'items' in data:
            for idx, item in enumerate(data['items']):
                result = {
                    'title': item.get('title', ''),
                    'link': item.get('link', ''),
                    'image_link': item.get('image', {}).get('thumbnailLink', ''),
                    'context_link': item.get('image', {}).get('contextLink', ''),
                    'width': item.get('image', {}).get('width', 0),
                    'height': item.get('image', {}).get('height', 0)
                }
                results.append(result)

                logger.debug(
                    f"Processed image result {idx + 1}",
                    extra={"extra_data": {"title": result['title'], "image_link": result['image_link']}}
                )

        logger.info(
            f"Google image search completed",
            extra={"extra_data": {"images_found": len(results), "query": query}}
        )

        return results
    except requests.exceptions.HTTPError as e:
        logger.error(
            f"HTTP error during Google image search",
            extra={"extra_data": {"status_code": e.response.status_code, "query": query}},
            exc_info=True
        )
        return [{"error": f"Image search failed with HTTP {e.response.status_code}: {str(e)}"}]
    except Exception as e:
        logger.error(
            f"Unexpected error during Google image search",
            extra={"extra_data": {"query": query, "error": str(e)}},
            exc_info=True
        )
        return [{"error": f"Image search failed: {str(e)}"}]
