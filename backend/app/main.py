"""FastAPI application entrypoint."""

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Create the FastAPI application instance."""
    return FastAPI(
        title="Enterprise Multi-Agent OS API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )


app = create_app()
