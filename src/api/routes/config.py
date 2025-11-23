"""Configuration routes for the chatbot API."""
import os
from fastapi import APIRouter
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

router = APIRouter()


@router.get("/api/config/maps-api-key")
async def get_maps_api_key():
    """Get the Google Maps API key for the frontend."""
    maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    
    if not maps_api_key:
        return {"api_key": None, "error": "Maps API key not configured"}
    
    return {"api_key": maps_api_key}
