from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from app.services.subdomain_service import SubdomainService
from typing import Optional, Dict, Any
from app.core.redis import get_cache, set_cache, delete_cache
import asyncio

router = APIRouter(
    prefix="/domains",
    tags=["domains"],
    responses={404: {"description": "Not found"}},
)

# Global cache for large domain progress
background_tasks = {}

@router.get("/")
async def search_by_domain(
    domain: str = Query(..., description="The domain to search for subdomains"),
    use_cache: Optional[bool] = Query(True, description="Whether to use cached results if available"),
    background_task: Optional[bool] = Query(False, description="Run as a background task for large domains")
):
    """
    Search for subdomains for a given domain using subfinder and crt.sh
    """
    if not domain:
        raise HTTPException(status_code=400, detail="Domain parameter is required")
    
    # Check if we already have a background task running for this domain
    task_key = f"task:domain:{domain}"
    if task_key in background_tasks:
        task_status = background_tasks[task_key]
        if task_status["status"] == "running":
            return {
                "domain": domain,
                "status": "processing",
                "message": f"Processing domain {domain}. Please check back later.",
                "progress": task_status.get("progress", 0)
            }
        elif task_status["status"] == "completed":
            # Return the completed result and clean up
            result = task_status["result"]
            del background_tasks[task_key]
            return result
    
    # Check cache first if enabled
    if use_cache:
        cache_key = f"domain:{domain}"
        cached_data = await get_cache(cache_key)
        if cached_data:
            return cached_data
    
    try:
        # If it's a potentially large domain and background_task is True,
        # process it in the background
        if background_task:
            background_tasks[task_key] = {
                "status": "running",
                "progress": 0
            }
            
            # Start background task
            asyncio.create_task(process_domain_in_background(domain, task_key))
            
            return {
                "domain": domain,
                "status": "processing",
                "message": f"Started processing domain {domain} in the background. Please check back later.",
                "progress": 0
            }
        else:
            # Process synchronously
            results = await SubdomainService.get_subdomains_by_domain(domain, use_cache)
            return results
    except Exception as e:
        # Clean up the background task entry if it exists
        if task_key in background_tasks:
            del background_tasks[task_key]
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

async def process_domain_in_background(domain: str, task_key: str):
    """Process a domain in the background and update the task status"""
    try:
        # Update progress
        background_tasks[task_key]["progress"] = 10
        
        # Process the domain
        result = await SubdomainService.get_subdomains_by_domain(domain, True)
        
        # Store the result and mark as completed
        background_tasks[task_key].update({
            "status": "completed",
            "result": result,
            "progress": 100
        })
    except Exception as e:
        # Handle errors
        background_tasks[task_key].update({
            "status": "error",
            "error": str(e),
            "progress": 0
        })

@router.get("/status")
async def check_domain_status(
    domain: str = Query(..., description="The domain to check status for")
):
    """
    Check the status of a background domain processing task
    """
    task_key = f"task:domain:{domain}"
    if task_key in background_tasks:
        task_status = background_tasks[task_key]
        return {
            "domain": domain,
            "status": task_status["status"],
            "progress": task_status.get("progress", 0)
        }
    else:
        return {
            "domain": domain,
            "status": "not_found",
            "message": "No background task found for this domain"
        }

@router.get("/clear-cache")
async def clear_domain_cache(
    domain: str = Query(..., description="The domain to clear cache for")
):
    """
    Clear the cache for a specific domain
    """
    if not domain:
        raise HTTPException(status_code=400, detail="Domain parameter is required")
    
    try:
        await delete_cache(f"domain:{domain}")
        return {"message": f"Cache cleared for domain {domain}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}") 