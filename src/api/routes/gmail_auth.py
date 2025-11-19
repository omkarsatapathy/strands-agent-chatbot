"""Gmail OAuth authentication routes."""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
from ...tools.gmail import GmailAuthManager
from ...logging_config import get_logger

logger = get_logger("chatbot.api.gmail_auth")

router = APIRouter(prefix="/auth/gmail", tags=["Gmail Authentication"])


class AuthStatusResponse(BaseModel):
    """Response model for auth status."""
    authenticated: bool
    user_id: str
    message: str


@router.get("/authorize")
async def authorize_gmail(request: Request, user_id: str = "default"):
    """
    Initiate Gmail OAuth authorization flow.

    Args:
        request: FastAPI request object
        user_id: User identifier (default: "default")

    Returns:
        Redirect to Google OAuth consent screen
    """
    try:
        auth_manager = GmailAuthManager(user_id)

        # Build redirect URI
        base_url = str(request.base_url).rstrip('/')
        redirect_uri = f"{base_url}/auth/gmail/callback"

        # Get authorization URL
        auth_url = auth_manager.get_authorization_url(redirect_uri)

        logger.info(
            "Gmail authorization initiated",
            extra={"extra_data": {"user_id": user_id, "redirect_uri": redirect_uri}}
        )

        return RedirectResponse(url=auth_url)

    except FileNotFoundError as e:
        logger.error(f"Credentials file not found: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Gmail credentials.json not found. Please configure OAuth credentials."
        )
    except Exception as e:
        logger.error(f"Failed to initiate authorization: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Authorization failed: {str(e)}")


@router.get("/callback")
async def gmail_callback(request: Request, code: Optional[str] = None, error: Optional[str] = None):
    """
    Handle OAuth callback from Google.

    Args:
        request: FastAPI request object
        code: Authorization code from Google
        error: Error message if authorization failed

    Returns:
        Success or error response
    """
    if error:
        logger.error(f"OAuth authorization failed: {error}")
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": error,
                "message": "Gmail authorization was denied or failed."
            }
        )

    if not code:
        logger.error("No authorization code received")
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "missing_code",
                "message": "No authorization code received from Google."
            }
        )

    try:
        # Get user_id from query params (default to "default")
        user_id = request.query_params.get("state", "default")

        auth_manager = GmailAuthManager(user_id)

        # Build redirect URI
        base_url = str(request.base_url).rstrip('/')
        redirect_uri = f"{base_url}/auth/gmail/callback"

        # Exchange code for credentials
        creds = auth_manager.exchange_code(code, redirect_uri)

        logger.info(
            "Gmail authorization successful",
            extra={"extra_data": {"user_id": user_id}}
        )

        # Return HTML response with success message
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Gmail Authorization Successful</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }
                .container {
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 10px 25px rgba(0,0,0,0.2);
                    text-align: center;
                    max-width: 500px;
                }
                h1 { color: #4CAF50; margin-bottom: 20px; }
                p { color: #666; font-size: 16px; line-height: 1.6; }
                .success-icon { font-size: 64px; margin-bottom: 20px; }
                .button {
                    display: inline-block;
                    margin-top: 20px;
                    padding: 12px 30px;
                    background: #667eea;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                }
                .button:hover { background: #5568d3; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success-icon">✅</div>
                <h1>Authorization Successful!</h1>
                <p>Your Gmail account has been successfully connected.</p>
                <p>You can now use Gmail features in the chatbot.</p>
                <a href="/" class="button">Go to Chatbot</a>
            </div>
        </body>
        </html>
        """

        return HTMLResponse(content=html_content)

    except Exception as e:
        logger.error(f"Failed to exchange authorization code: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "exchange_failed",
                "message": f"Failed to complete authorization: {str(e)}"
            }
        )


@router.get("/status", response_model=AuthStatusResponse)
async def gmail_auth_status(user_id: str = "default"):
    """
    Check Gmail authentication status.

    Args:
        user_id: User identifier (default: "default")

    Returns:
        Authentication status
    """
    try:
        auth_manager = GmailAuthManager(user_id)
        is_authenticated = auth_manager.is_authenticated()

        logger.info(
            "Gmail auth status checked",
            extra={"extra_data": {"user_id": user_id, "authenticated": is_authenticated}}
        )

        return AuthStatusResponse(
            authenticated=is_authenticated,
            user_id=user_id,
            message="Authenticated" if is_authenticated else "Not authenticated"
        )

    except Exception as e:
        logger.error(f"Failed to check auth status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


@router.post("/revoke")
async def revoke_gmail_auth(user_id: str = "default"):
    """
    Revoke Gmail authentication.

    Args:
        user_id: User identifier (default: "default")

    Returns:
        Success message
    """
    try:
        auth_manager = GmailAuthManager(user_id)

        # Delete token file
        import os
        if os.path.exists(auth_manager.token_path):
            os.remove(auth_manager.token_path)
            logger.info(
                "Gmail auth revoked",
                extra={"extra_data": {"user_id": user_id}}
            )
            return {"success": True, "message": "Gmail authentication revoked successfully"}
        else:
            return {"success": False, "message": "No active authentication found"}

    except Exception as e:
        logger.error(f"Failed to revoke auth: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Revoke failed: {str(e)}")


# Import HTMLResponse
from fastapi.responses import HTMLResponse
