# Gmail Authentication & Authorization Guide

This guide helps you set up, troubleshoot, and manage Gmail authentication for the chatbot.

---

## Table of Contents
1. [Initial Setup](#initial-setup)
2. [Changing Email ID](#changing-email-id)
3. [Troubleshooting Authorization Issues](#troubleshooting-authorization-issues)
4. [Re-authorizing Gmail](#re-authorizing-gmail)
5. [Common Errors & Solutions](#common-errors--solutions)

---

## Initial Setup

### Prerequisites
- Google Account with Gmail access
- Google Cloud Console project with Gmail API enabled
- OAuth 2.0 credentials (credentials.json)

### Step 1: Configure Your Email in the System

1. Open the configuration file:
   ```bash
   nano /Users/omkarsatapaphy/python_works/agentic_chatbot/src/config.py
   ```

2. Update the `GMAIL_USER_ID` with your email:
   ```python
   GMAIL_USER_ID: str = os.getenv("GMAIL_USER_ID", "your-email@gmail.com")
   ```

3. You can also set it via environment variable in `.env`:
   ```
   GMAIL_USER_ID=your-email@gmail.com
   ```

### Step 2: Place OAuth Credentials

Ensure your `credentials.json` file is in the correct location:
```
/Users/omkarsatapaphy/python_works/agentic_chatbot/frontend/database/gmail_credentials/credentials.json
```

### Step 3: Authorize Gmail Access

1. Start your server:
   ```bash
   python backend.py
   ```

2. Visit the authorization URL in your browser:
   ```
   http://localhost:8000/auth/gmail/authorize?user_id=your-email@gmail.com
   ```

3. Sign in with your Google account and grant permissions

4. You'll be redirected to a success page

5. Verify authentication:
   ```
   http://localhost:8000/auth/gmail/status?user_id=your-email@gmail.com
   ```

---

## Changing Email ID

If you want to use a different Gmail account:

### Method 1: Update Configuration (Recommended)

1. **Update the config file:**
   ```bash
   nano /Users/omkarsatapaphy/python_works/agentic_chatbot/src/config.py
   ```

2. **Change the email:**
   ```python
   GMAIL_USER_ID: str = os.getenv("GMAIL_USER_ID", "new-email@gmail.com")
   ```

3. **Add new email as test user in Google Cloud Console:**
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Navigate to **APIs & Services** → **OAuth consent screen**
   - Scroll to **Test users** section
   - Click **+ ADD USERS**
   - Enter your new email: `new-email@gmail.com`
   - Click **Save**

4. **Authorize the new email:**
   ```
   http://localhost:8000/auth/gmail/authorize?user_id=new-email@gmail.com
   ```

5. **Restart your server:**
   ```bash
   lsof -ti:8000 | xargs kill -9 2>/dev/null; sleep 1; python backend.py
   ```

### Method 2: Use Environment Variable

1. **Create or edit `.env` file:**
   ```bash
   nano /Users/omkarsatapaphy/python_works/agentic_chatbot/.env
   ```

2. **Add or update:**
   ```
   GMAIL_USER_ID=new-email@gmail.com
   ```

3. **Follow steps 3-5 from Method 1**

---

## Troubleshooting Authorization Issues

### Check Current Authorization Status

```bash
curl http://localhost:8000/auth/gmail/status?user_id=your-email@gmail.com
```

Expected response if authenticated:
```json
{
  "authenticated": true,
  "user_id": "your-email@gmail.com",
  "message": "Authenticated"
}
```

### Check Token Files

List existing token files:
```bash
ls -la /Users/omkarsatapaphy/python_works/agentic_chatbot/frontend/database/gmail_credentials/
```

You should see:
- `credentials.json` - OAuth client credentials
- `token_your-email@gmail.com.pickle` - Your authentication token

---

## Re-authorizing Gmail

If authorization breaks or stops working:

### Step 1: Revoke Current Authorization

**Option A: Using API endpoint**
```bash
curl -X POST "http://localhost:8000/auth/gmail/revoke?user_id=your-email@gmail.com"
```

**Option B: Manually delete token file**
```bash
rm /Users/omkarsatapaphy/python_works/agentic_chatbot/frontend/database/gmail_credentials/token_your-email@gmail.com.pickle
```

### Step 2: Clear Browser Cookies (Optional)

If you're changing accounts, clear cookies for:
- `accounts.google.com`
- `localhost:8000`

### Step 3: Re-authorize

1. Visit authorization URL:
   ```
   http://localhost:8000/auth/gmail/authorize?user_id=your-email@gmail.com
   ```

2. Complete Google OAuth flow

3. Verify authorization:
   ```bash
   curl http://localhost:8000/auth/gmail/status?user_id=your-email@gmail.com
   ```

### Step 4: Restart Server

```bash
lsof -ti:8000 | xargs kill -9 2>/dev/null; sleep 1; python backend.py
```

---

## Common Errors & Solutions

### Error: "Not authenticated"

**Cause:** Token file doesn't exist or is invalid

**Solution:**
1. Check if token file exists:
   ```bash
   ls -la frontend/database/gmail_credentials/ | grep token
   ```

2. If missing, authorize again:
   ```
   http://localhost:8000/auth/gmail/authorize?user_id=your-email@gmail.com
   ```

---

### Error: "redirect_uri_mismatch"

**Cause:** OAuth redirect URI in Google Cloud Console doesn't match the one used in the request

**Solution:**
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to **APIs & Services** → **Credentials**
3. Click on your OAuth 2.0 Client ID
4. Under **Authorized redirect URIs**, ensure you have:
   ```
   http://localhost:8000/auth/gmail/callback
   ```
5. Click **Save**
6. Try authorization again

---

### Error: "Access blocked: app has not completed verification"

**Cause:** You're not added as a test user in Google Cloud Console

**Solution:**
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to **APIs & Services** → **OAuth consent screen**
3. Scroll to **Test users** section
4. Click **+ ADD USERS**
5. Enter your email address
6. Click **Save**
7. Try authorization again

---

### Error: "credentials.json not found"

**Cause:** OAuth credentials file is missing or in wrong location

**Solution:**
1. Download `credentials.json` from Google Cloud Console:
   - Go to **APIs & Services** → **Credentials**
   - Click **Download JSON** on your OAuth 2.0 Client ID

2. Place it in the correct location:
   ```bash
   cp ~/Downloads/credentials.json frontend/database/gmail_credentials/credentials.json
   ```

3. Verify placement:
   ```bash
   ls -la frontend/database/gmail_credentials/credentials.json
   ```

---

### Error: "invalid_grant" or "Token has been expired or revoked"

**Cause:** Refresh token is invalid or revoked

**Solution:**
1. Delete the old token:
   ```bash
   rm frontend/database/gmail_credentials/token_your-email@gmail.com.pickle
   ```

2. Re-authorize:
   ```
   http://localhost:8000/auth/gmail/authorize?user_id=your-email@gmail.com
   ```

---

### Error: Token file exists but still showing "Not authenticated"

**Cause:** Token file might be corrupted or for a different user ID

**Solution:**
1. Check which token files exist:
   ```bash
   ls -la frontend/database/gmail_credentials/
   ```

2. If you see a token with a different ID (e.g., `token_wrNrsjMDSOeaoCQYikmSKBZa4SaVQg.pickle`), copy it:
   ```bash
   cp frontend/database/gmail_credentials/token_OLDID.pickle \
      frontend/database/gmail_credentials/token_your-email@gmail.com.pickle
   ```

3. Or delete all tokens and re-authorize:
   ```bash
   rm frontend/database/gmail_credentials/token_*.pickle
   ```
   ```
   http://localhost:8000/auth/gmail/authorize?user_id=your-email@gmail.com
   ```

---

## Testing Gmail Integration

### Test 1: Check Authentication Status

```bash
curl http://localhost:8000/auth/gmail/status?user_id=your-email@gmail.com
```

### Test 2: Run Standalone Test Script

Create a test file:
```bash
nano test_gmail_auth.py
```

Add this code:
```python
import sys
sys.path.insert(0, '/Users/omkarsatapaphy/python_works/agentic_chatbot')

from src.tools.gmail import gmail_auth_status, fetch_gmail_messages

# Check auth status
print("Checking authentication...")
status = gmail_auth_status(user_id="your-email@gmail.com")
print(status)

# Try fetching emails
if status['authenticated']:
    print("\nFetching emails...")
    result = fetch_gmail_messages(max_results=5, user_id="your-email@gmail.com")
    print(f"Fetched {result.get('count', 0)} emails")
else:
    print("Not authenticated. Please authorize first.")
```

Run it:
```bash
python test_gmail_auth.py
```

### Test 3: Test in Chatbot

1. Start the server
2. Create a new chat session
3. Ask: "Check my Gmail authentication status"
4. Ask: "Show me my recent emails"

---

## Configuration Reference

### Default Settings

Located in `src/config.py`:

```python
# Gmail Configuration
GMAIL_USER_ID: str = "omkarsatapathy001@gmail.com"  # Your Gmail address
GMAIL_DEFAULT_MAX_RESULTS: int = 25                  # Default number of emails to fetch
GMAIL_FETCH_FULL_BODY: bool = True                   # Fetch full email body (not just snippet)
```

### Environment Variables (Optional)

Add to `.env` file:
```
GMAIL_USER_ID=your-email@gmail.com
GMAIL_DEFAULT_MAX_RESULTS=25
GMAIL_FETCH_FULL_BODY=True
```

---

## File Structure

```
agentic_chatbot/
├── src/
│   ├── config.py                          # Gmail configuration
│   ├── tools/
│   │   ├── gmail.py                       # Gmail tool implementation
│   │   └── gmailAuthGuide.md             # This guide
│   └── api/
│       └── routes/
│           └── gmail_auth.py              # OAuth endpoints
├── frontend/
│   └── database/
│       └── gmail_credentials/
│           ├── credentials.json           # OAuth client credentials (download from Google)
│           └── token_<email>.pickle      # User auth tokens (auto-generated)
└── .env                                   # Environment variables (optional)
```

---

## Security Best Practices

1. **Never commit credentials to git:**
   - `credentials.json` is already in `.gitignore`
   - `*.pickle` token files are also ignored

2. **Use environment variables for production:**
   ```
   export GMAIL_USER_ID=your-email@gmail.com
   ```

3. **Rotate credentials periodically:**
   - Download new `credentials.json` from Google Cloud Console
   - Re-authorize all users

4. **Limit OAuth scopes:**
   - Currently using: `gmail.readonly`
   - Only allows reading emails, not sending or deleting

---

## Additional Resources

- [Gmail API Documentation](https://developers.google.com/gmail/api)
- [OAuth 2.0 Guide](https://developers.google.com/identity/protocols/oauth2)
- [Google Cloud Console](https://console.cloud.google.com)
- Main Setup Guide: `/Users/omkarsatapaphy/python_works/agentic_chatbot/GMAIL_SETUP.md`

---

## Quick Reference Commands

```bash
# Check authentication status
curl http://localhost:8000/auth/gmail/status?user_id=your-email@gmail.com

# Authorize Gmail
open http://localhost:8000/auth/gmail/authorize?user_id=your-email@gmail.com

# Revoke authorization
curl -X POST http://localhost:8000/auth/gmail/revoke?user_id=your-email@gmail.com

# List token files
ls -la frontend/database/gmail_credentials/

# Delete all tokens
rm frontend/database/gmail_credentials/token_*.pickle

# Restart server
lsof -ti:8000 | xargs kill -9 2>/dev/null; sleep 1; python backend.py
```

---

## Support

If you continue to experience issues:

1. Check the server logs for detailed error messages
2. Verify all steps in this guide have been completed
3. Ensure your Google Cloud project has Gmail API enabled
4. Confirm your email is added as a test user in OAuth consent screen

---

**Last Updated:** November 19, 2025
**Version:** 1.0
