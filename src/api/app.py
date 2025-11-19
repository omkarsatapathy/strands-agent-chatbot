"""FastAPI application initialization and configuration."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from src.database import DatabaseManager
from src.config import Config
from src.logging_config import setup_logging
from .routes import chat, sessions, messages, documents, models, gmail_auth

# Setup logging
logger = setup_logging(Config.LOG_LEVEL, Config.LOG_TO_FILE, Config.LOG_TO_CONSOLE)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    # Initialize FastAPI app
    app = FastAPI(title="Chatbot API")

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    # Mount static files
    app.mount("/static", StaticFiles(directory="frontend"), name="static")

    # Initialize database manager
    db_manager = DatabaseManager()

    # Inject database manager into route modules
    sessions.set_db_manager(db_manager)
    messages.set_db_manager(db_manager)
    documents.set_db_manager(db_manager)

    # Include routers
    app.include_router(chat.router)
    app.include_router(sessions.router)
    app.include_router(messages.router)
    app.include_router(documents.router)
    app.include_router(models.router)
    app.include_router(gmail_auth.router)

    # Root endpoint
    @app.get("/")
    async def read_root():
        """Serve the main HTML page."""
        return FileResponse("frontend/index.html")

    # Health check endpoint
    @app.get("/api/health")
    async def health_check():
        """Check API health status."""
        return {"status": "healthy", "llm_url": Config.LLAMA_CPP_URL}

    logger.info("FastAPI application initialized successfully")
    return app
