from fastapi import FastAPI
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

@app.on_event("startup")
async def startup_event():
    # Create necessary directories
    os.makedirs("output", exist_ok=True) 