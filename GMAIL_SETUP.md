# Gmail Integration Setup Guide

## Overview
This guide will help you integrate Gmail with your chatbot using OAuth 2.0 authentication.

## Prerequisites
- Google Account
- Google Cloud Console access

---

## Step 1: Google Cloud Console Setup

### 1.1 Create a Project
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click the project dropdown at the top
3. Click **"New Project"**
4. Name it (e.g., "Chatbot Gmail Integration")
5. Click **"Create"**

### 1.2 Enable Gmail API
1. In the left sidebar, go to **"APIs & Services"** → **"Library"**
2. Search for **"Gmail API"**
3. Click on it and press **"Enable"**

### 1.3 Configure OAuth Consent Screen
1. Go to **"APIs & Services"** → **"OAuth consent screen"**
2. Select **"External"** (unless you have Google Workspace)
3. Click **"Create"**
4. Fill in required fields:
   - **App name**: Your Chatbot Name
   - **User support email**: Your email
   - **Developer contact**: Your email
5. Click **"Save and Continue"**

### 1.4 Add Scopes
1. On the "Scopes" page, click **"Add or Remove Scopes"**
2. Filter and add: `https://www.googleapis.com/auth/gmail.readonly`
3. Click **"Update"** and then **"Save and Continue"**

### 1.5 Add Test Users
1. On the "Test users" page, click **"Add Users"**
2. Add your Gmail address (the one you want to read emails from)
3. Click **"Save and Continue"**

### 1.6 Create OAuth 2.0 Credentials
1. Go to **"APIs & Services"** → **"Credentials"**
2. Click **"Create Credentials"** → **"OAuth client ID"**
3. Select **"Web application"**
4. Name it (e.g., "Gmail Bot Client")
5. Under **"Authorized redirect URIs"**, add:
   ```
   http://localhost:8000/auth/gmail/callback
   ```
   (Change `localhost:8000` to your domain if deploying)
6. Click **"Create"**

### 1.7 Download Credentials
1. A popup appears with your Client ID and Secret
2. Click **"Download JSON"**
3. Save the file as `credentials.json`
4. Move it to: `frontend/database/gmail_credentials/credentials.json`

---

## Step 2: Install Dependencies

Run the following command to install required packages:

```bash
pip install -r requirements.txt
```

This will install:
- `google-auth`
- `google-auth-oauthlib`
- `google-auth-httplib2`
- `google-api-python-client`

---

## Step 3: Directory Setup

The credentials directory is created automatically, but ensure it exists:

```bash
mkdir -p frontend/database/gmail_credentials
```

Place your `credentials.json` file here:
```
frontend/database/gmail_credentials/credentials.json
```

**IMPORTANT**: Add this to your `.gitignore`:
```
frontend/database/gmail_credentials/*.json
frontend/database/gmail_credentials/*.pickle
```

---

## Step 4: Start Your Server

Start your FastAPI backend:

```bash
python backend.py
```

---

## Step 5: Authenticate Gmail

### 5.1 Visit Authorization URL
Open your browser and go to:
```
http://localhost:8000/auth/gmail/authorize
```

### 5.2 Grant Permissions
1. Select your Google account
2. Click **"Continue"** (may show "app not verified" - this is normal for test apps)
3. Click **"Continue"** again
4. Review permissions and click **"Allow"**

### 5.3 Success!
You'll be redirected to a success page. Your Gmail is now connected!

---

## Step 6: Using Gmail in the Chatbot

### Check Authentication Status
Ask the chatbot:
```
Check my Gmail authentication status
```

### Fetch Recent Emails
Ask the chatbot:
```
Show me my recent emails
```

### Search Emails
Ask the chatbot:
```
Show me unread emails
```
or
```
Show me emails from john@example.com
```

### Query Parameters
The Gmail tool supports Gmail search syntax:
- `is:unread` - Only unread messages
- `from:email@example.com` - From specific sender
- `subject:important` - Messages with "important" in subject
- `has:attachment` - Messages with attachments
- `after:2024/01/01` - Messages after a date

---

## API Endpoints

### GET `/auth/gmail/authorize`
Initiates OAuth flow

### GET `/auth/gmail/callback`
OAuth callback endpoint (handled automatically)

### GET `/auth/gmail/status`
Check authentication status
```bash
curl http://localhost:8000/auth/gmail/status?user_id=default
```

### POST `/auth/gmail/revoke`
Revoke Gmail authentication
```bash
curl -X POST http://localhost:8000/auth/gmail/revoke?user_id=default
```

---

## Troubleshooting

### "credentials.json not found"
- Ensure `credentials.json` is in `frontend/database/gmail_credentials/`
- Check file permissions

### "Not authenticated" error
- Visit `/auth/gmail/authorize` to authenticate
- Check if token file exists: `frontend/database/gmail_credentials/token_default.pickle`

### "Access denied" or "invalid_grant"
- Re-authenticate via `/auth/gmail/authorize`
- Ensure you're using a test user added in Google Cloud Console

### "API not enabled"
- Make sure Gmail API is enabled in Google Cloud Console

---

## Security Notes

1. **Never commit credentials to git**:
   - Add `*.json` and `*.pickle` in the credentials directory to `.gitignore`

2. **Token Storage**:
   - Tokens are stored as pickle files in `frontend/database/gmail_credentials/`
   - These contain refresh tokens for long-term access

3. **Production Deployment**:
   - Use environment variables for sensitive paths
   - Consider encrypting token files
   - Use HTTPS for OAuth callbacks
   - Verify your app in Google Cloud Console for production use

---

## File Structure

```
agentic_chatbot/
├── src/
│   ├── tools/
│   │   └── gmail.py                    # Gmail tool implementation
│   └── api/
│       └── routes/
│           └── gmail_auth.py           # OAuth endpoints
├── frontend/
│   └── database/
│       └── gmail_credentials/
│           ├── credentials.json        # OAuth client credentials (download from Google)
│           └── token_default.pickle   # User tokens (auto-generated)
└── requirements.txt                    # Updated with Google libraries
```

---

## Next Steps

1. Follow the setup steps above
2. Test authentication by visiting `/auth/gmail/authorize`
3. Try asking the chatbot: "Show me my recent emails"
4. Explore Gmail search queries for advanced filtering

Enjoy your Gmail-integrated chatbot! 📧✨
