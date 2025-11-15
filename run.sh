#!/bin/bash
# Run the FastAPI backend with auto-reload

uvicorn backend:app --host 0.0.0.0 --port 8000 --reload --reload-dir . --reload-dir src --reload-dir frontend
