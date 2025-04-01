from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import os

from app.api.endpoints import domains, organizations, health
from app.core.config import settings

app = FastAPI(
    title="Subdomain Finder API",
    description="API for finding subdomains using subfinder, crt.sh, and httpx",
    version="2.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(domains.router, prefix="/api")
app.include_router(organizations.router, prefix="/api")

# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint - API information
    """
    return {
        "name": "Subdomain Finder API",
        "version": "2.0",
        "description": "API for finding subdomains using subfinder, crt.sh, and httpx",
        "endpoints": {
            "/api/domains": "Search for subdomains by domain name",
            "/api/organizations": "Search for domains by organization name",
            "/health": "API health check",
            "/docs": "API documentation (Swagger UI)"
        }
    }

# Direct health check
@app.get("/health")
async def root_health():
    """
    Root health check endpoint
    """
    return {"status": "ok"}

@app.on_event("startup")
async def startup_event():
    # Create necessary directories
    os.makedirs("output", exist_ok=True) 