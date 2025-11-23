"""Google Maps grounding tool using Gemini API for location-aware responses."""
import json
from typing import Optional, Dict, Any
from google import genai
from google.genai import types
from strands import tool
from ..config import Config
from ..logging_config import get_logger

logger = get_logger("chatbot.tools.google_maps")

# Initialize Gemini client
client = genai.Client(api_key=Config.GEMINI_API_KEY)

# Default coordinates (Hyderabad, India)
DEFAULT_LATITUDE = 17.473863
DEFAULT_LONGITUDE = 78.351742


def query_maps_with_gemini(
    query: str,
    latitude: float = DEFAULT_LATITUDE,
    longitude: float = DEFAULT_LONGITUDE,
    include_widget: bool = True
) -> Dict[str, Any]:
    """
    Query Google Maps using Gemini's Maps grounding feature.

    Args:
        query: The location-related query
        latitude: Latitude coordinate for location context
        longitude: Longitude coordinate for location context
        include_widget: Whether to include widget token for map rendering

    Returns:
        Dictionary with response text, widget token, and grounding metadata
    """
    try:
        logger.info(f"Maps query: '{query}' at ({latitude}, {longitude})")

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=query,
            config=types.GenerateContentConfig(
                # Turn on grounding with Google Maps
                tools=[types.Tool(google_maps=types.GoogleMaps(enable_widget=include_widget))],
                # Provide the relevant location context
                tool_config=types.ToolConfig(
                    retrieval_config=types.RetrievalConfig(
                        lat_lng=types.LatLng(
                            latitude=latitude,
                            longitude=longitude
                        )
                    )
                )
            )
        )

        result = {
            "text": response.text,
            "widget_token": None,
            "places": [],
            "coordinates": {"latitude": latitude, "longitude": longitude}
        }

        # Extract grounding metadata for widget rendering
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                metadata = candidate.grounding_metadata

                # Extract widget context token for rendering maps widget
                if hasattr(metadata, 'google_maps_widget_context_token') and metadata.google_maps_widget_context_token:
                    result["widget_token"] = metadata.google_maps_widget_context_token
                    logger.info("Maps widget token extracted")

                # Extract grounding chunks (places from Maps)
                if hasattr(metadata, 'grounding_chunks') and metadata.grounding_chunks:
                    for chunk in metadata.grounding_chunks:
                        # Check for maps data (places)
                        if hasattr(chunk, 'maps') and chunk.maps:
                            place_data = {
                                "place_id": getattr(chunk.maps, 'place_id', ''),
                                "title": getattr(chunk.maps, 'title', ''),
                                "uri": getattr(chunk.maps, 'uri', '')
                            }
                            result["places"].append(place_data)
                            logger.debug(f"Found place: {place_data['title']}")

        has_places = len(result["places"]) > 0
        logger.info(f"Maps response received: {len(result['text'])} chars, places: {len(result['places'])}, widget_token: {result['widget_token'] is not None}")
        return result

    except Exception as e:
        logger.error(f"Google Maps query failed: {e}")
        raise


def format_maps_response(result: Dict[str, Any]) -> str:
    """
    Format maps response with optional widget metadata for frontend rendering.

    Args:
        result: Dictionary from query_maps_with_gemini

    Returns:
        Formatted string with text and embedded metadata
    """
    response_text = result["text"]

    # Include maps data if we have places or widget token
    has_maps_data = result.get("widget_token") or len(result.get("places", [])) > 0

    if has_maps_data:
        metadata = {
            "maps_widget": {
                "context_token": result.get("widget_token"),
                "coordinates": result["coordinates"],
                "places": result.get("places", [])[:10]  # Limit to 10 places
            }
        }
        # Append as hidden metadata marker for frontend parsing
        response_text += f"\n\n<!--MAPS_WIDGET:{json.dumps(metadata)}-->"
        logger.info(f"Added maps widget metadata with {len(metadata['maps_widget']['places'])} places")

    return response_text


@tool
def search_nearby_places(
    query: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None
) -> str:
    """
    Search for nearby places, restaurants, businesses, or points of interest.

    Use this tool when the user asks about:
    - Nearby restaurants, cafes, shops, or businesses
    - Places to visit or attractions in an area
    - Finding specific types of establishments (hospitals, ATMs, gas stations, etc.)

    Args:
        query: What to search for (e.g., "best Italian restaurants", "nearby hospitals")
        latitude: Optional latitude coordinate (defaults to Hyderabad)
        longitude: Optional longitude coordinate (defaults to Hyderabad)

    Returns:
        Information about nearby places matching the query with optional maps widget
    """
    try:
        lat = latitude if latitude is not None else DEFAULT_LATITUDE
        lng = longitude if longitude is not None else DEFAULT_LONGITUDE

        result = query_maps_with_gemini(query, lat, lng)
        return format_maps_response(result)

    except Exception as e:
        logger.error(f"search_nearby_places error: {e}")
        return f"Failed to search nearby places: {str(e)}"


@tool
def get_directions(
    origin: str,
    destination: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None
) -> str:
    """
    Get directions and travel information between two locations.

    Use this tool when the user asks about:
    - How to get from one place to another
    - Travel routes and directions
    - Distance and estimated travel time between locations

    Args:
        origin: Starting location or address
        destination: Destination location or address
        latitude: Optional latitude for context (defaults to Hyderabad)
        longitude: Optional longitude for context (defaults to Hyderabad)

    Returns:
        Directions and travel information with optional maps widget
    """
    try:
        lat = latitude if latitude is not None else DEFAULT_LATITUDE
        lng = longitude if longitude is not None else DEFAULT_LONGITUDE

        query = f"How do I get from {origin} to {destination}? Provide directions and estimated travel time."
        result = query_maps_with_gemini(query, lat, lng)
        return format_maps_response(result)

    except Exception as e:
        logger.error(f"get_directions error: {e}")
        return f"Failed to get directions: {str(e)}"


@tool
def get_traffic_info(
    location: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None
) -> str:
    """
    Get current traffic conditions and updates for an area.

    Use this tool when the user asks about:
    - Current traffic conditions
    - Road congestion or traffic jams
    - Best time to travel or commute

    Args:
        location: Optional specific location or route to check traffic for
        latitude: Optional latitude coordinate (defaults to Hyderabad)
        longitude: Optional longitude coordinate (defaults to Hyderabad)

    Returns:
        Current traffic information and conditions with optional maps widget
    """
    try:
        lat = latitude if latitude is not None else DEFAULT_LATITUDE
        lng = longitude if longitude is not None else DEFAULT_LONGITUDE

        if location:
            query = f"What is the current traffic situation near {location}? Include any congestion, road conditions, or delays."
        else:
            query = "What is the current traffic situation in this area? Include any congestion, major road conditions, or delays."

        result = query_maps_with_gemini(query, lat, lng)
        return format_maps_response(result)

    except Exception as e:
        logger.error(f"get_traffic_info error: {e}")
        return f"Failed to get traffic info: {str(e)}"


@tool
def get_place_details(
    place_name: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None
) -> str:
    """
    Get detailed information about a specific place or business.

    Use this tool when the user asks about:
    - Operating hours of a business
    - Reviews and ratings of a place
    - Contact information or address
    - Details about a specific restaurant, shop, or attraction

    Args:
        place_name: Name of the place to get details about
        latitude: Optional latitude for context (defaults to Hyderabad)
        longitude: Optional longitude for context (defaults to Hyderabad)

    Returns:
        Detailed information about the place with optional maps widget
    """
    try:
        lat = latitude if latitude is not None else DEFAULT_LATITUDE
        lng = longitude if longitude is not None else DEFAULT_LONGITUDE

        query = f"Tell me about {place_name}. Include its address, operating hours, ratings, reviews, and any other relevant details."
        result = query_maps_with_gemini(query, lat, lng)
        return format_maps_response(result)

    except Exception as e:
        logger.error(f"get_place_details error: {e}")
        return f"Failed to get place details: {str(e)}"


@tool
def explore_area(
    area: Optional[str] = None,
    interests: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None
) -> str:
    """
    Explore and discover interesting places in an area based on interests.

    Use this tool when the user wants to:
    - Discover what's around them
    - Find things to do in an area
    - Get recommendations based on interests
    - Plan activities or outings

    Args:
        area: Optional specific area or neighborhood to explore
        interests: Optional interests or preferences (e.g., "family-friendly", "nightlife", "outdoor activities")
        latitude: Optional latitude coordinate (defaults to Hyderabad)
        longitude: Optional longitude coordinate (defaults to Hyderabad)

    Returns:
        Recommendations and interesting places to explore with optional maps widget
    """
    try:
        lat = latitude if latitude is not None else DEFAULT_LATITUDE
        lng = longitude if longitude is not None else DEFAULT_LONGITUDE

        if area and interests:
            query = f"What are some interesting places to visit in {area} for someone interested in {interests}? Include popular attractions, hidden gems, and recommendations."
        elif area:
            query = f"What are the best places to visit and things to do in {area}? Include popular attractions, restaurants, and local favorites."
        elif interests:
            query = f"What are some nearby places for someone interested in {interests}? Include recommendations and suggestions."
        else:
            query = "What are some interesting places to visit and things to do nearby? Include popular attractions, restaurants, and local favorites."

        result = query_maps_with_gemini(query, lat, lng)
        return format_maps_response(result)

    except Exception as e:
        logger.error(f"explore_area error: {e}")
        return f"Failed to explore area: {str(e)}"
