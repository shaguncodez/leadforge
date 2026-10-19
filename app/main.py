from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.database import create_tables
from app.middleware import RequestLoggingMiddleware
from app.routers import (
    activities_router,
    analytics_router,
    auth_router,
    leads_router,
    tasks_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler: creates tables on startup."""
    await create_tables()
    yield


app = FastAPI(
    title="LeadForge API",
    description="AI-Assisted Lead Management & Scoring Platform with real-time analytics and follow-up tracking.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# CORS middleware allowing all origins (supporting GitHub Pages frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(auth_router)
app.include_router(leads_router)
app.include_router(activities_router)
app.include_router(tasks_router)
app.include_router(analytics_router)


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for container orchestrators and monitoring."""
    return {
        "status": "healthy",
        "service": "LeadForge API",
        "version": "1.0.0",
    }


# Mount static directory if it exists
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir, html=True), name="static")


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint redirects to interactive API documentation."""
    return RedirectResponse(url="/docs")
