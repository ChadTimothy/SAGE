"""FastAPI application for SAGE backend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import chat_router, graph_router, learners_router, practice_router, sessions_router, voice_router

app = FastAPI(
    title="SAGE API",
    description="AI Tutor that teaches through conversation",
    version="0.1.0",
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(learners_router)
app.include_router(sessions_router)
app.include_router(chat_router)
app.include_router(graph_router)
app.include_router(practice_router)
app.include_router(voice_router)


@app.get("/")
def root() -> dict:
    """Root endpoint."""
    return {"message": "SAGE API", "version": "0.1.0"}


@app.get("/health")
def health() -> dict:
    """Health check endpoint."""
    return {"status": "healthy"}
