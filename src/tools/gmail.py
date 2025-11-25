"""Gmail tool for fetching emails using OAuth 2.0."""
import os
import pickle
import base64
from typing import Dict, Any, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from ..config import Config
from ..logging_config import get_logger
from strands import tool

logger = get_logger("chatbot.tools.gmail")

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
os.makedirs(Config.GMAIL_CREDENTIALS_DIR, exist_ok=True)


class GmailAuthManager:
    """Manages Gmail OAuth authentication."""

    def __init__(self, user_id: str = None):
        """Initialize Gmail auth manager."""
        self.user_id = user_id or Config.GMAIL_USER_ID
        self.token_path = os.path.join(Config.GMAIL_CREDENTIALS_DIR, f"token_{self.user_id}.pickle")
        self.credentials_path = os.path.join(Config.GMAIL_CREDENTIALS_DIR, "credentials.json")

    def get_credentials(self) -> Optional[Credentials]:
        """Get valid user credentials."""
        creds = None
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(self.token_path, 'wb') as token:
                    pickle.dump(creds, token)
                logger.info("Credentials refreshed successfully")
            except Exception as e:
                logger.error(f"Failed to refresh credentials: {str(e)}")
                creds = None
        return creds

    def save_credentials(self, creds: Credentials):
        """Save user credentials."""
        with open(self.token_path, 'wb') as token:
            pickle.dump(creds, token)
        logger.info(f"Credentials saved for user: {self.user_id}")

    def get_authorization_url(self, redirect_uri: str) -> str:
        """Get OAuth authorization URL."""
        if not os.path.exists(self.credentials_path):
            raise FileNotFoundError(
                f"credentials.json not found at {self.credentials_path}. "
                "Please download it from Google Cloud Console."
            )
        flow = Flow.from_client_secrets_file(self.credentials_path, scopes=SCOPES, redirect_uri=redirect_uri)
        auth_url, _ = flow.authorization_url(access_type='offline', include_granted_scopes='true', prompt='consent')
        return auth_url

    def exchange_code(self, code: str, redirect_uri: str) -> Credentials:
        """Exchange authorization code for credentials."""
        flow = Flow.from_client_secrets_file(self.credentials_path, scopes=SCOPES, redirect_uri=redirect_uri)
        flow.fetch_token(code=code)
        creds = flow.credentials
        self.save_credentials(creds)
        return creds

    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        creds = self.get_credentials()
        return creds is not None and creds.valid


def _clean_email_text(text: str) -> str:
    """Clean up email text by removing extra whitespace and formatting."""
    import re
    # Replace multiple newlines with double newline
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Replace non-breaking spaces
    text = text.replace('\xa0', ' ')
    # Remove lines that are just whitespace
    lines = [line.rstrip() for line in text.split('\n')]
    text = '\n'.join(line for line in lines if line.strip() or line == '')
    # Remove excessive spaces
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


def _get_email_body(payload: Dict) -> str:
    """Extract email body from message payload."""
    body = ""

    # Try to get text/plain first (cleaner than HTML)
    if 'parts' in payload:
        for part in payload['parts']:
            # Handle nested multipart
            if 'parts' in part:
                body = _get_email_body(part)
                if body:
                    return body
            # Get text/plain
            if part['mimeType'] == 'text/plain' and 'data' in part.get('body', {}):
                body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                return body

        # Fall back to text/html if no plain text
        for part in payload['parts']:
            if part['mimeType'] == 'text/html' and 'data' in part.get('body', {}):
                body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                return body

    # Single part message
    elif 'data' in payload.get('body', {}):
        body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
        return body

    return ""


@tool
def fetch_gmail_messages(
    max_results: int = None,
    query: str = "",
    user_id: str = None
) -> str:
    """
    Strands tool: Fetch the most recent Gmail messages from inbox.

    Fetches emails from the inbox and sorts them by receive time (newest first) using Gmail's internalDate.
    Includes all inbox emails (Primary, Promotions, Social, Updates tabs).

    Args:
        max_results: Maximum number of messages to fetch (default 15)
        query: Optional Gmail search query for filtering (e.g., "is:unread", "from:example@gmail.com", "newer_than:7d", "category:primary")
        user_id: User identifier (default from config)

    Returns:
        JSON string containing list of messages with id, subject, from, date, snippet, and full body content, sorted newest first
    """
    import json
    max_results = max_results or Config.GMAIL_DEFAULT_MAX_RESULTS
    auth_manager = GmailAuthManager(user_id)

    logger.info("Starting Gmail message fetch", extra={"extra_data": {
        "max_results": max_results, "query": query, "user_id": auth_manager.user_id
    }})

    if not auth_manager.is_authenticated():
        logger.warning("User not authenticated for Gmail")
        return json.dumps({
            "error": "Not authenticated",
            "message": "Please authenticate with Gmail first. Visit /auth/gmail to authorize."
        })

    try:
        service = build('gmail', 'v1', credentials=auth_manager.get_credentials())
        max_results = min(max_results, Config.GMAIL_MAX_RESULTS_LIMIT)

        logger.debug("Fetching messages from Gmail API")
        # Fetch from INBOX (includes all inbox emails regardless of category)
        # Gmail API returns messages mostly in reverse chronological order, but not guaranteed
        # We'll fetch and sort by internalDate to ensure newest first
        results = service.users().messages().list(
            userId='me',
            maxResults=max_results,
            labelIds=['INBOX'],
            q=query
        ).execute()
        messages = results.get('messages', [])

        if not messages:
            logger.info("No messages found")
            return json.dumps({"messages": [], "count": 0, "message": "No messages found matching the query."})

        # Fetch detailed message data with internalDate for sorting
        detailed_messages = []
        for msg in messages:
            try:
                msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
                headers = msg_data['payload']['headers']
                body = _get_email_body(msg_data['payload'])

                # Clean up the body text
                if body:
                    body = _clean_email_text(body)

                if len(body) > Config.GMAIL_BODY_MAX_LENGTH:
                    body = body[:Config.GMAIL_BODY_MAX_LENGTH] + "... [truncated]"

                message_info = {
                    'id': msg_data['id'],
                    'subject': next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject'),
                    'from': next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown'),
                    'date': next((h['value'] for h in headers if h['name'].lower() == 'date'), 'Unknown'),
                    'snippet': msg_data.get('snippet', ''),
                    'internalDate': int(msg_data.get('internalDate', 0))  # Store for sorting
                }

                if body:
                    message_info['body'] = body
                detailed_messages.append(message_info)
            except HttpError as e:
                logger.warning(f"Failed to fetch message {msg['id']}: {str(e)}")
                continue

        # Sort messages by internalDate (newest first) to guarantee correct order
        detailed_messages.sort(key=lambda x: x.get('internalDate', 0), reverse=True)

        # Remove internalDate from response (not needed by agent)
        for msg in detailed_messages:
            msg.pop('internalDate', None)

        logger.info(f"Successfully fetched {len(detailed_messages)} Gmail messages",
            extra={"extra_data": {"count": len(detailed_messages), "query": query}})

        return json.dumps({"messages": detailed_messages, "count": len(detailed_messages), "query": query}, ensure_ascii=False)

    except HttpError as e:
        logger.error("Gmail API error", extra={"extra_data": {"error": str(e)}}, exc_info=True)
        return json.dumps({"error": "Gmail API error", "message": f"Failed to fetch messages: {str(e)}"})
    except Exception as e:
        logger.error("Unexpected error fetching Gmail messages", extra={"extra_data": {"error": str(e)}}, exc_info=True)
        return json.dumps({"error": "Unexpected error", "message": f"Failed to fetch messages: {str(e)}"})


@tool
def gmail_auth_status(user_id: str = None) -> str:
    """
    Strands tool: Check Gmail authentication status.

    Args:
        user_id: User identifier (default from config)

    Returns:
        JSON string with authentication status
    """
    import json
    auth_manager = GmailAuthManager(user_id)
    is_authenticated = auth_manager.is_authenticated()

    logger.info("Gmail auth status checked", extra={"extra_data": {
        "user_id": auth_manager.user_id, "is_authenticated": is_authenticated
    }})

    return json.dumps({
        "authenticated": is_authenticated,
        "user_id": auth_manager.user_id,
        "message": "Authenticated" if is_authenticated else "Not authenticated. Please authorize via /auth/gmail"
    })
