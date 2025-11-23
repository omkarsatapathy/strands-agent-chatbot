"""Image analysis API endpoint."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from src.tools.image_analysis import process_image_message
from src.logging_config import get_logger

logger = get_logger("chatbot.routes.image")

router = APIRouter(prefix="/api", tags=["image"])


class ImageAnalysisRequest(BaseModel):
    """Request model for image analysis."""
    image_base64: str  # Base64 encoded image data (without data URL prefix)
    message: Optional[str] = None  # Optional question/prompt about the image


class ImageAnalysisResponse(BaseModel):
    """Response model for image analysis."""
    description: str
    success: bool = True


@router.post("/image/analyze", response_model=ImageAnalysisResponse)
async def analyze_image(request: ImageAnalysisRequest):
    """
    Analyze an image using Gemini Vision API.

    Args:
        request: ImageAnalysisRequest containing base64 image and optional message

    Returns:
        ImageAnalysisResponse with the analysis result
    """
    try:
        logger.info(f"Image analysis request received, message: {request.message[:50] if request.message else 'None'}...")

        # Process the image
        description = process_image_message(
            image_base64=request.image_base64,
            user_message=request.message or ""
        )

        return ImageAnalysisResponse(
            description=description,
            success=True
        )

    except Exception as e:
        logger.error(f"Image analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
