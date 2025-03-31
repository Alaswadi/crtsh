from fastapi import APIRouter
import subprocess
import sys
from pydantic import BaseModel
from typing import Dict, Any, List

router = APIRouter(
    prefix="/health",
    tags=["health"],
)

class HealthStatus(BaseModel):
    status: str
    components: Dict[str, Any]
    tools: Dict[str, bool]

@router.get("/", response_model=HealthStatus)
async def health_check():
    """
    Health check endpoint to verify the API and its components are running properly
    """
    # Check Redis connection
    redis_status = "ok"
    try:
        from app.core.redis import get_redis_pool
        redis = await get_redis_pool()
        await redis.ping()
        await redis.close()
    except Exception as e:
        redis_status = f"error: {str(e)}"
    
    # Check subfinder availability
    subfinder_available = check_tool_availability("subfinder", "-version")
    
    # Check httpx availability
    httpx_available = check_tool_availability("httpx", "-version")
    
    return HealthStatus(
        status="ok",
        components={
            "redis": redis_status,
            "api": "ok",
        },
        tools={
            "subfinder": subfinder_available,
            "httpx": httpx_available,
        }
    )

def check_tool_availability(tool_name, version_flag):
    """Check if a CLI tool is available and working"""
    try:
        subprocess.run(
            [tool_name, version_flag], 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False 