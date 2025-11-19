"""Gmail tool for fetching emails using OAuth 2.0."""
import os
import pickle
from typing import Dict, Any, List, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from ..config import Config
from ..logging_config import get_logger
from strands import tool

logger = get_logger("chatbot.tools.gmail")

# OAuth 2.0 scopes for Gmail API
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Path to store credentials
CREDENTIALS_DIR = "frontend/database/gmail_credentials"
os.makedirs(CREDENTIALS_DIR, exist_ok=True)


class GmailAuthManager:
    """Manages Gmail OAuth authentication."""

    def __init__(self, user_id: str = "default"):
        """
        Initialize Gmail auth manager.

        Args:
            user_id: Unique identifier for the user (default: "default")
        """
        self.user_id = user_id
        self.token_path = os.path.join(CREDENTIALS_DIR, f"token_{user_id}.pickle")
        self.credentials_path = os.path.join(CREDENTIALS_DIR, "credentials.json")

    def get_credentials(self) -> Optional[Credentials]:
        """
        Get valid user credentials.

        Returns:
            Valid credentials or None if not available
        """
        creds = None

        # Load existing credentials
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)

        # Refresh if expired
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Save refreshed credentials
                with open(self.token_path, 'wb') as token:
                    pickle.dump(creds, token)
                logger.info("Credentials refreshed successfully")
            except Exception as e:
                logger.error(f"Failed to refresh credentials: {str(e)}")
                creds = None

        return creds

    def save_credentials(self, creds: Credentials):
        """
        Save user credentials.

        Args:
            creds: Credentials to save
        """
        with open(self.token_path, 'wb') as token:
            pickle.dump(creds, token)
        logger.info(f"Credentials saved for user: {self.user_id}")

    def get_authorization_url(self, redirect_uri: str) -> str:
        """
        Get OAuth authorization URL.

        Args:
            redirect_uri: Redirect URI for OAuth callback

        Returns:
            Authorization URL
        """
        if not os.path.exists(self.credentials_path):
            raise FileNotFoundError(
                f"credentials.json not found at {self.credentials_path}. "
                "Please download it from Google Cloud Console."
            )

        flow = Flow.from_client_secrets_file(
            self.credentials_path,
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )

        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )

        return auth_url

    def exchange_code(self, code: str, redirect_uri: str) -> Credentials:
        """
        Exchange authorization code for credentials.

        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Redirect URI used in authorization

        Returns:
            User credentials
        """
        flow = Flow.from_client_secrets_file(
            self.credentials_path,
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )

        flow.fetch_token(code=code)
        creds = flow.credentials

        # Save credentials
        self.save_credentials(creds)

        return creds

    def is_authenticated(self) -> bool:
        """
        Check if user is authenticated.

        Returns:
            True if valid credentials exist
        """
        creds = self.get_credentials()
        return creds is not None and creds.valid


@tool
def fetch_gmail_messages(
    max_results: int = 10,
    query: str = "",
    user_id: str = "default"
) -> Dict[str, Any]:
    """
    Strands tool: Fetch Gmail messages for the authenticated user.

    This tool retrieves email messages from Gmail. The user must authenticate
    first via OAuth 2.0. Use query parameter for filtering (e.g., "is:unread",
    "from:example@gmail.com", "subject:important").

    Args:
        max_results: Maximum number of messages to fetch (default: 10, max: 50)
        query: Gmail search query for filtering messages (default: "" for all messages)
        user_id: User identifier (default: "default")

    Returns:
        Dictionary containing list of messages or error information
    """
    auth_manager = GmailAuthManager(user_id)

    logger.info(
        "Starting Gmail message fetch",
        extra={"extra_data": {"max_results": max_results, "query": query, "user_id": user_id}}
    )

    # Check authentication
    if not auth_manager.is_authenticated():
        logger.warning("User not authenticated for Gmail")
        return {
            "error": "Not authenticated",
            "message": "Please authenticate with Gmail first. Visit /auth/gmail to authorize."
        }

    try:
        # Get credentials
        creds = auth_manager.get_credentials()

        # Build Gmail service
        service = build('gmail', 'v1', credentials=creds)

        # Limit max_results
        max_results = min(max_results, 50)

        # Fetch messages
        logger.debug(f"Fetching messages from Gmail API")
        results = service.users().messages().list(
            userId='me',
            maxResults=max_results,
            q=query
        ).execute()

        messages = results.get('messages', [])

        if not messages:
            logger.info("No messages found")
            return {
                "messages": [],
                "count": 0,
                "message": "No messages found matching the query."
            }

        # Fetch full message details
        detailed_messages = []
        for msg in messages:
            try:
                msg_data = service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='full'
                ).execute()

                # Extract message details
                headers = msg_data['payload']['headers']
                subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
                from_email = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown')
                date = next((h['value'] for h in headers if h['name'].lower() == 'date'), 'Unknown')

                # Get snippet
                snippet = msg_data.get('snippet', '')

                detailed_messages.append({
                    'id': msg_data['id'],
                    'subject': subject,
                    'from': from_email,
                    'date': date,
                    'snippet': snippet
                })

            except HttpError as e:
                logger.warning(f"Failed to fetch message {msg['id']}: {str(e)}")
                continue

        logger.info(
            f"Successfully fetched {len(detailed_messages)} Gmail messages",
            extra={"extra_data": {"count": len(detailed_messages), "query": query}}
        )

        return {
            "messages": detailed_messages,
            "count": len(detailed_messages),
            "query": query
        }

    except HttpError as e:
        logger.error(
            f"Gmail API error",
            extra={"extra_data": {"error": str(e)}},
            exc_info=True
        )
        return {
            "error": "Gmail API error",
            "message": f"Failed to fetch messages: {str(e)}"
        }
    except Exception as e:
        logger.error(
            f"Unexpected error fetching Gmail messages",
            extra={"extra_data": {"error": str(e)}},
            exc_info=True
        )
        return {
            "error": "Unexpected error",
            "message": f"Failed to fetch messages: {str(e)}"
        }


@tool
def gmail_auth_status(user_id: str = "default") -> Dict[str, Any]:
    """
    Strands tool: Check Gmail authentication status.

    Args:
        user_id: User identifier (default: "default")

    Returns:
        Dictionary with authentication status
    """
    auth_manager = GmailAuthManager(user_id)
    is_authenticated = auth_manager.is_authenticated()

    logger.info(
        "Gmail auth status checked",
        extra={"extra_data": {"user_id": user_id, "is_authenticated": is_authenticated}}
    )

    return {
        "authenticated": is_authenticated,
        "user_id": user_id,
        "message": "Authenticated" if is_authenticated else "Not authenticated. Please authorize via /auth/gmail"
    }
