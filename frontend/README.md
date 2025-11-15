# Frontend - AI Chatbot

A modern, responsive chat interface for the AI Chatbot powered by Strands agents.

## Features

- Clean, modern UI with gradient theme
- Real-time chat interface
- Typing indicators
- Web search integration
- Conversation history
- Auto-resizing text input
- Responsive design

## How to Launch the Frontend

### Option 1: Using the FastAPI Backend (Recommended)

The frontend is automatically served by the FastAPI backend:

1. Make sure you have all dependencies installed (see main README)
2. Start the FastAPI server from the project root:
   ```bash
   python backend.py
   ```
3. Open your browser and navigate to:
   ```
   http://localhost:8000
   ```

### Option 2: Using a Simple HTTP Server

If you want to run the frontend separately for development:

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Start a simple HTTP server:

   **Using Python 3:**
   ```bash
   python -m http.server 8080
   ```

   **Using Node.js (if you have http-server installed):**
   ```bash
   npx http-server -p 8080
   ```

3. Open your browser and navigate to:
   ```
   http://localhost:8080
   ```

**Note:** If running separately, make sure to update the `API_BASE_URL` in `app.js` to point to your backend server (default: `http://localhost:8000`).

## File Structure

```
frontend/
├── index.html      # Main HTML file
├── styles.css      # Stylesheet
├── app.js          # JavaScript application logic
└── README.md       # This file
```

## Configuration

To change the backend API URL, edit the `API_BASE_URL` constant in `app.js`:

```javascript
const API_BASE_URL = 'http://localhost:8000';
```

## Usage

1. **Chat**: Type your message in the text input and press Enter or click the send button
2. **Web Search**: Type a search query and click the "Web Search" button
3. **Clear Chat**: Click the "Clear Chat" button to reset the conversation

## Browser Support

- Chrome (recommended)
- Firefox
- Safari
- Edge

Modern browsers with ES6+ support required.
