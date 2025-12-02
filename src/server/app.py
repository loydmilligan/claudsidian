"""FastAPI server for Claudsidian HTTP API.

This module provides the main FastAPI application with CORS support,
lifespan management, and basic configuration for the Claudsidian API server.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.server.routes.capture import router as capture_router
from src.server.routes.status import router as status_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Handle application startup and shutdown events.

    This context manager is called when the application starts up and shuts down.
    Use this to initialize resources on startup and clean them up on shutdown.

    Args:
        app: The FastAPI application instance

    Yields:
        None: Control to the application
    """
    # Startup
    logger.info("Starting Claudsidian API server")
    logger.info(f"Server version: {app.version}")

    yield

    # Shutdown
    logger.info("Shutting down Claudsidian API server")


async def log_requests(request: Request, call_next):
    """Simple request logging middleware.

    Args:
        request: The incoming request
        call_next: The next middleware or route handler

    Returns:
        The response from the next handler
    """
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"{request.method} {request.url.path} - {response.status_code}")
    return response


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured FastAPI application instance
    """
    app = FastAPI(
        title="Claudsidian",
        description="AI-powered knowledge capture for Obsidian",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Configure CORS middleware
    # Allow requests from localhost and 127.0.0.1 on any port
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost",
            "http://localhost:*",
            "http://127.0.0.1",
            "http://127.0.0.1:*",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add request logging middleware
    app.middleware("http")(log_requests)

    # Include routers
    app.include_router(capture_router)
    app.include_router(status_router)

    # Version info endpoint
    @app.get("/")
    async def root() -> JSONResponse:
        """Root endpoint returning API information.

        Returns:
            JSONResponse: API name, version, and status
        """
        return JSONResponse({
            "name": app.title,
            "version": app.version,
            "description": app.description,
            "status": "running"
        })

    @app.get("/health")
    async def health() -> JSONResponse:
        """Health check endpoint.

        Returns:
            JSONResponse: Health status
        """
        return JSONResponse({"status": "healthy"})

    return app


# Create the application instance
app = create_app()


def run_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    """Run the FastAPI server with uvicorn.

    Args:
        host: Host address to bind to. Use "127.0.0.1" for localhost only,
              or "0.0.0.0" to allow LAN access. Defaults to "127.0.0.1".
        port: Port number to bind to. Defaults to 8765.
    """
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    # Configure basic logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    run_server()
