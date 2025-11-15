# AI Chatbot with Strands Agents

A simple AI chatbot application using Strands agents framework, FastAPI backend, and a modern web frontend.

## Project Structure

```
agentic_chatbot/
├── backend.py              # FastAPI backend server
├── src/                    # Python source files
│   ├── agent.py           # Strands agent configuration
│   └── tools.py           # Custom tools (Google Search)
├── frontend/              # Frontend files
│   ├── index.html        # Main HTML page
│   ├── styles.css        # Stylesheet
│   ├── app.js            # JavaScript application
│   └── README.md         # Frontend documentation
└── README.md             # This file
```

## Features

- Strands agent integration with custom LlamaCpp backend
- Google Custom Search integration (web and image search)
- Modern, responsive chat interface
- FastAPI backend with CORS support
- Real-time conversation handling

## Prerequisites

- Python 3.8+
- LlamaCpp server running at `http://127.0.0.1:8033`
- pip package manager

## Installation

1. Clone or navigate to the project directory:
   ```bash
   cd /Users/omkarsatapaphy/python_works/agentic_chatbot
   ```

2. Install required Python packages:
   ```bash
   pip install fastapi uvicorn strands-agents requests pydantic
   ```

3. Make sure your LlamaCpp server is running at `http://127.0.0.1:8033`

## Running the Application

### Start the Backend Server

From the project root directory:

```bash
python backend.py
```

The server will start at `http://localhost:8000`

### Access the Frontend

Once the backend is running, open your browser and navigate to:

```
http://localhost:8000
```

## API Endpoints

### Chat Endpoint
```
POST /api/chat
Content-Type: application/json

{
  "message": "Your message here",
  "conversation_history": []
}
```

### Search Endpoint
```
POST /api/search
Content-Type: application/json

{
  "query": "search query",
  "num_results": 5,
  "search_type": "web"  // or "image"
}
```

### Health Check
```
GET /api/health
```

## Configuration

### LlamaCpp Server URL

To change the LlamaCpp server URL, edit the `llm_url` parameter in `backend.py`:

```python
agent = create_chatbot_agent(llm_url="http://127.0.0.1:8033")
```

### Google API Credentials

The Google Custom Search API credentials are configured in `src/tools.py`. To use your own:

1. Get an API key from [Google Cloud Console](https://console.cloud.google.com/)
2. Create a Custom Search Engine at [Google CSE](https://programmablesearchengine.google.com/)
3. Update the credentials in `src/tools.py`:

```python
api_key = 'YOUR_API_KEY'
search_engine_id = 'YOUR_SEARCH_ENGINE_ID'
```

## Development

### Adding New Tools

To add new tools for the Strands agent:

1. Create your tool function in `src/tools.py`
2. Import and register it in `src/agent.py`
3. Update the agent initialization in `backend.py`

### Customizing the Agent

Edit `src/agent.py` to customize:
- System prompts
- Model parameters (temperature, max tokens)
- Tool configurations

## Troubleshooting

### LlamaCpp Connection Issues

If you get connection errors:
1. Verify LlamaCpp is running: `curl http://127.0.0.1:8033/health`
2. Check the port number matches in `backend.py`
3. Ensure no firewall is blocking the connection

### CORS Issues

If you encounter CORS errors, ensure the backend CORS middleware is properly configured in `backend.py`.

### Frontend Not Loading

1. Check that the backend server is running
2. Verify the `frontend/` directory exists with all files
3. Check browser console for errors

## Next Steps

This is a basic implementation. You can enhance it by:

- Implementing proper Strands tool decorators
- Adding conversation memory/persistence
- Implementing streaming responses
- Adding authentication
- Enhancing error handling
- Adding more tools (calculator, file operations, etc.)
- Improving the UI/UX

## License

MIT

## Support

For Strands documentation, visit: https://strandsagents.com/latest/documentation/docs/
