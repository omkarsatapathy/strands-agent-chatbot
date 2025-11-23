"""FastAPI backend for the chatbot application - Main entry point."""
import sys
import warnings
from pathlib import Path

# Suppress OpenTelemetry context detach warnings (known issue with async context management)
warnings.filterwarnings("ignore", message=".*Failed to detach context.*")
warnings.filterwarnings("ignore", message=".*was created in a different Context.*")

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.api import create_app
from src.config import Config

# Create the FastAPI application
app = create_app()


if __name__ == "__main__":
    import uvicorn
    host, port = Config.get_server_config()
    uvicorn.run(
        "backend:app",
        host=host,
        port=port,
        reload=True,
        reload_dirs=[".", "src", "frontend"],
        log_level="warning"  # Reduce log verbosity (only warnings and errors)
    )
