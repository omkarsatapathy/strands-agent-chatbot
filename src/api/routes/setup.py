"""Setup API routes for managing initial configuration."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
import os
import re

router = APIRouter(prefix="/api/setup", tags=["setup"])

# Path to the .env file
ENV_FILE_PATH = Path(__file__).parent.parent.parent.parent / ".env"
SETUP_FLAG_FILE = Path(__file__).parent.parent.parent.parent / ".setup_complete"


class APIKeysRequest(BaseModel):
    """Request model for saving API keys."""
    OPENAI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None


class SetupStatusResponse(BaseModel):
    """Response model for setup status."""
    setup_complete: bool


@router.get("/status", response_model=SetupStatusResponse)
async def get_setup_status():
    """Check if initial setup has been completed."""
    setup_complete = SETUP_FLAG_FILE.exists()
    return SetupStatusResponse(setup_complete=setup_complete)


@router.post("/save-keys")
async def save_api_keys(keys: APIKeysRequest):
    """Save API keys to the .env file."""
    try:
        # Read existing .env content
        env_content = ""
        if ENV_FILE_PATH.exists():
            with open(ENV_FILE_PATH, "r") as f:
                env_content = f.read()

        # Update or add each key
        if keys.OPENAI_API_KEY:
            env_content = update_env_variable(env_content, "OPENAI_API_KEY", keys.OPENAI_API_KEY)

        if keys.GEMINI_API_KEY:
            env_content = update_env_variable(env_content, "GEMINI_API_KEY", keys.GEMINI_API_KEY)

        # Write back to .env file
        with open(ENV_FILE_PATH, "w") as f:
            f.write(env_content)

        return {"success": True, "message": "API keys saved successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save API keys: {str(e)}")


@router.post("/complete")
async def mark_setup_complete():
    """Mark the setup as complete."""
    try:
        # Create the setup complete flag file
        SETUP_FLAG_FILE.touch()
        return {"success": True, "message": "Setup marked as complete"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to mark setup complete: {str(e)}")


@router.post("/reset")
async def reset_setup():
    """Reset the setup status (for testing/development)."""
    try:
        if SETUP_FLAG_FILE.exists():
            SETUP_FLAG_FILE.unlink()
        return {"success": True, "message": "Setup reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset setup: {str(e)}")


def update_env_variable(content: str, key: str, value: str) -> str:
    """Update or add an environment variable in the .env content."""
    # Pattern to match the key (with optional spaces around =)
    pattern = rf'^{re.escape(key)}\s*=.*$'

    # Check if key exists
    if re.search(pattern, content, re.MULTILINE):
        # Replace existing value
        content = re.sub(pattern, f"{key}={value}", content, flags=re.MULTILINE)
    else:
        # Add new key at the end
        if content and not content.endswith('\n'):
            content += '\n'
        content += f"{key}={value}\n"

    return content
