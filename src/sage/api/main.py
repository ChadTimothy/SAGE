"""FastAPI application for SAGE backend."""

import contextlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.routing import Mount

from .routes import (
    auth_router,
    chat_router,
    graph_router,
    learners_router,
    mcp_router,
    oauth_router,
    practice_router,
    scenarios_router,
    sessions_router,
    voice_router,
)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for MCP server."""
    # Import here to avoid circular imports
    from sage.mcp import mcp

    async with mcp.session_manager.run():
        yield


app = FastAPI(
    title="SAGE API",
    description="AI Tutor that teaches through conversation",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS for frontend and external integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # Local development
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
        "http://127.0.0.1:3000",
        # ChatGPT Apps
        "https://chat.openai.com",
        "https://chatgpt.com",
        # Claude Desktop (uses local proxy, but may need CORS)
        "http://localhost:*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(oauth_router)
app.include_router(mcp_router)
app.include_router(learners_router)
app.include_router(sessions_router)
app.include_router(chat_router)
app.include_router(graph_router)
app.include_router(practice_router)
app.include_router(scenarios_router)
app.include_router(voice_router)


# Mount MCP server for ChatGPT/Claude integration
def _mount_mcp_server():
    """Mount the MCP streamable HTTP server."""
    from sage.mcp import mcp

    # Mount MCP server at /mcp for streamable HTTP transport
    app.routes.append(
        Mount("/mcp", app=mcp.streamable_http_app())
    )


_mount_mcp_server()


@app.get("/")
def root() -> dict:
    """Root endpoint."""
    return {"message": "SAGE API", "version": "0.1.0"}


@app.get("/health")
def health() -> dict:
    """Health check endpoint."""
    return {"status": "healthy"}
