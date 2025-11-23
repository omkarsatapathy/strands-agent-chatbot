"""Image analysis tool using Google Gemini Vision API."""
import base64
import io
from typing import Optional
from PIL import Image
import google.generativeai as genai
from strands import tool
from ..config import Config
from ..logging_config import get_logger

logger = get_logger("chatbot.tools.image_analysis")

# Configure Gemini
genai.configure(api_key=Config.GEMINI_API_KEY)


def analyze_image_with_gemini(image_data: bytes, prompt: str = "Describe what you see in this image in detail.") -> str:
    """
    Analyze an image using Gemini Vision API.

    Args:
        image_data: Raw image bytes (supports JPEG, PNG, WebP, HEIC)
        prompt: The prompt/question to ask about the image

    Returns:
        Description or analysis from Gemini
    """
    try:
        # Convert bytes to PIL Image
        img = Image.open(io.BytesIO(image_data))

        # Convert to RGB if necessary (handles RGBA, etc.)
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')

        logger.info(f"Analyzing image: {img.size}, mode: {img.mode}")

        # Use gemini-2.5-flash for vision
        model = genai.GenerativeModel("gemini-2.5-flash")

        response = model.generate_content([prompt, img])

        logger.info("Image analysis completed successfully")
        return response.text

    except Exception as e:
        logger.error(f"Image analysis failed: {e}")
        raise


@tool
def analyze_image(image_base64: str, question: Optional[str] = None) -> str:
    """
    Analyze an image and describe its contents or answer questions about it.

    Use this tool when the user shares an image and wants to know what's in it,
    or asks questions about an image they've shared.

    Args:
        image_base64: Base64 encoded image data
        question: Optional specific question about the image. If not provided,
                  a general description will be given.

    Returns:
        A detailed description or answer about the image content.
    """
    try:
        # Decode base64 image
        image_data = base64.b64decode(image_base64)

        # Default prompt if no question provided
        prompt = question if question else "Describe what you see in this image in detail. Include any text, objects, people, colors, and notable features."

        result = analyze_image_with_gemini(image_data, prompt)
        return result

    except Exception as e:
        logger.error(f"analyze_image tool error: {e}")
        return f"Failed to analyze image: {str(e)}"


def process_image_message(image_base64: str, user_message: str = "") -> str:
    """
    Process an image message from the chat - standalone function for direct API use.

    Args:
        image_base64: Base64 encoded image data (may include data URL prefix)
        user_message: User's message/question about the image

    Returns:
        Analysis result from Gemini
    """
    try:
        # Handle data URL format (data:image/jpeg;base64,...)
        if ',' in image_base64 and image_base64.startswith('data:'):
            image_base64 = image_base64.split(',')[1]

        # Clean up any whitespace or newlines
        image_base64 = image_base64.strip().replace('\n', '').replace('\r', '').replace(' ', '')

        # Add padding if needed
        padding = 4 - len(image_base64) % 4
        if padding != 4:
            image_base64 += '=' * padding

        logger.info(f"Decoding base64 image, length: {len(image_base64)}")

        image_data = base64.b64decode(image_base64)
        logger.info(f"Decoded image data, size: {len(image_data)} bytes")

        prompt = user_message if user_message else "Describe what you see in this image in detail."

        return analyze_image_with_gemini(image_data, prompt)

    except Exception as e:
        logger.error(f"process_image_message error: {e}")
        return f"Failed to process image: {str(e)}"
