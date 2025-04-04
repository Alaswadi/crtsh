from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from app.services.subdomain_service import SubdomainService
from typing import Optional, Dict, Any
from app.core.redis import get_cache, set_cache, delete_cache
import asyncio
import logging

logger = logging.getLogger(__name__)

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
    background_task: Optional[bool] = Query(False, description="Run as a background task for large domains"),
    run_httpx: Optional[bool] = Query(False, description="Whether to run httpx scan (disabled by default)")
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
            # If we have cached data but httpx was not run and is now requested
            if run_httpx and cached_data.get("httpx_status") in ["not_started", "skipped", "error"]:
                # Create an explicitly sanitized list of subdomains
                sanitized_subdomains = []
                for subdomain in cached_data.get("subdomains", []):
                    if subdomain:  # Skip empty entries
                        sanitized_subdomains.append(str(subdomain))
                
                logger.info(f"Created sanitized list of {len(sanitized_subdomains)} subdomains from cache for {domain}")
                
                # Start httpx in a background task with the sanitized list
                asyncio.create_task(run_httpx_background(domain, sanitized_subdomains))
                
                # Update status to indicate httpx is running
                cached_data["httpx_status"] = "running"
                await set_cache(cache_key, cached_data)
            
            # Always include httpx results in the response if they exist
            if "httpx_results" in cached_data:
                logger.info(f"Returning cached data with {len(cached_data['httpx_results'])} HTTPX results")
                return cached_data
            
            return cached_data
    
    try:
        # If it's a potentially large domain and background_task is True,
        # process it in the background
        if background_task:
            background_tasks[task_key] = {
                "status": "running",
                "progress": 0
            }
            
            # Start background task - but don't automatically run httpx
            asyncio.create_task(process_domain_in_background(domain, task_key, run_httpx=False))
            
            return {
                "domain": domain,
                "status": "processing",
                "message": f"Started processing domain {domain} in the background. Please check back later.",
                "progress": 0
            }
        else:
            # Always process synchronously without running httpx automatically
            logger.info(f"Processing domain {domain} synchronously with run_httpx={run_httpx}")
            results = await SubdomainService.get_subdomains_by_domain(domain, use_cache, run_httpx=run_httpx)
            
            # If explicit httpx scan was requested, run it in the background
            if run_httpx:
                # Create an explicitly sanitized list of subdomains
                sanitized_subdomains = []
                for subdomain in results.get("subdomains", []):
                    if subdomain:  # Skip empty entries
                        sanitized_subdomains.append(str(subdomain))
                
                logger.info(f"Created sanitized list of {len(sanitized_subdomains)} subdomains from sync result for {domain}")
                
                # Start httpx in a background task with the sanitized list
                asyncio.create_task(run_httpx_background(domain, sanitized_subdomains))
                results["httpx_status"] = "running"
            
            # Always include httpx results in the response if they exist
            if "httpx_results" in results:
                logger.info(f"Returning results with {len(results['httpx_results'])} HTTPX results")
            
            return results
    except Exception as e:
        # Clean up the background task entry if it exists
        if task_key in background_tasks:
            del background_tasks[task_key]
        logger.error(f"Error processing domain {domain}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

async def process_domain_in_background(domain: str, task_key: str, run_httpx: bool = True):
    """Process a domain in the background and update the task status"""
    try:
        # Update progress
        background_tasks[task_key]["progress"] = 10
        
        # Process the domain without running httpx immediately
        result = await SubdomainService.get_subdomains_by_domain(domain, True, run_httpx=False)
        
        # Update progress
        background_tasks[task_key]["progress"] = 50
        
        # Store the result and mark as completed
        background_tasks[task_key].update({
            "status": "completed",
            "result": result,
            "progress": 100
        })
        
        # If httpx is requested, run it in another background task
        if run_httpx and result.get("subdomains"):
            # Create an explicitly sanitized list of subdomains
            sanitized_subdomains = []
            for subdomain in result.get("subdomains", []):
                if subdomain:  # Skip empty entries
                    sanitized_subdomains.append(str(subdomain))
            
            logger.info(f"Created sanitized list of {len(sanitized_subdomains)} subdomains from background task for {domain}")
            
            # Start httpx in another background task with the sanitized list
            asyncio.create_task(run_httpx_background(domain, sanitized_subdomains))
            
    except Exception as e:
        logger.error(f"Error in background task for {domain}: {str(e)}")
        # Handle errors
        background_tasks[task_key].update({
            "status": "error",
            "error": str(e),
            "progress": 0
        })

async def run_httpx_background(domain: str, subdomains: list):
    """Run httpx in the background for a domain"""
    try:
        logger.info(f"Starting HTTPX scan for {domain} with {len(subdomains)} subdomains")
        
        # Update cache to indicate httpx is running
        cache_key = f"domain:{domain}"
        cached_data = await get_cache(cache_key)
        if cached_data:
            cached_data["httpx_status"] = "running"
            await set_cache(cache_key, cached_data)
        
        # Create a completely new list with explicit conversion to strings
        # This ensures no reference to the original list object is maintained
        sanitized_subdomains = []
        for subdomain in subdomains:
            if subdomain:  # Skip empty entries
                sanitized_subdomains.append(str(subdomain))
        
        logger.info(f"Created sanitized list of {len(sanitized_subdomains)} subdomains for {domain}")
        
        # Run httpx on the completely new list
        httpx_results = await SubdomainService.run_httpx_for_domain(domain, sanitized_subdomains)
        
        # Update the cache with the completed results
        cached_data = await get_cache(cache_key)
        if cached_data:
            if httpx_results.get("httpx_status") == "completed":
                cached_data.update({
                    "httpx_status": "completed",
                    "httpx_results": httpx_results.get("httpx_results", [])
                })
                logger.info(f"Updated cache with {len(httpx_results.get('httpx_results', []))} HTTPX results")
            else:
                cached_data.update({
                    "httpx_status": "error",
                    "httpx_error": httpx_results.get("httpx_error", "Unknown error")
                })
                logger.error(f"HTTPX scan failed: {httpx_results.get('httpx_error', 'Unknown error')}")
            
            await set_cache(cache_key, cached_data)
            
        logger.info(f"Completed HTTPX scan for {domain}")
    except Exception as e:
        logger.error(f"Error running httpx in background for {domain}: {str(e)}")
        
        # Update the cache with error status
        cache_key = f"domain:{domain}"
        cached_data = await get_cache(cache_key)
        if cached_data:
            cached_data["httpx_status"] = "error"
            cached_data["httpx_error"] = str(e)
            await set_cache(cache_key, cached_data)

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
        # Check if we have a cached result with httpx status
        cache_key = f"domain:{domain}"
        cached_data = await get_cache(cache_key)
        if cached_data and "httpx_status" in cached_data:
            return {
                "domain": domain,
                "status": "completed",
                "progress": 100,
                "httpx_status": cached_data["httpx_status"]
            }
        
        return {
            "domain": domain,
            "status": "not_found",
            "message": "No background task found for this domain"
        }

@router.get("/httpx")
async def run_httpx_scan(
    domain: str = Query(..., description="The domain to run httpx scan for"),
    use_cache: Optional[bool] = Query(True, description="Whether to use cached subdomains if available")
):
    """
    Run httpx scan on subdomains of a domain
    """
    if not domain:
        raise HTTPException(status_code=400, detail="Domain parameter is required")
    
    # Check if we have cached subdomains
    cache_key = f"domain:{domain}"
    cached_data = await get_cache(cache_key)
    
    if not cached_data or not cached_data.get("subdomains"):
        # If no cached subdomains, get them first
        try:
            cached_data = await SubdomainService.get_subdomains_by_domain(domain, use_cache, run_httpx=False)
        except Exception as e:
            logger.error(f"Error getting subdomains for HTTPX scan: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error getting subdomains: {str(e)}")
    
    # Create an explicitly sanitized list of subdomains
    sanitized_subdomains = []
    for subdomain in cached_data.get("subdomains", []):
        if subdomain:  # Skip empty entries
            sanitized_subdomains.append(str(subdomain))
    
    logger.info(f"Created sanitized list of {len(sanitized_subdomains)} subdomains for HTTPX endpoint for {domain}")
    
    # Start the httpx scan in the background with sanitized list
    asyncio.create_task(run_httpx_background(domain, sanitized_subdomains))
    
    # Update status to indicate httpx is running
    cached_data["httpx_status"] = "running"
    await set_cache(cache_key, cached_data)
    
    return {
        "domain": domain,
        "message": f"Started httpx scan for {domain} with {len(sanitized_subdomains)} subdomains",
        "status": "running",
        "total_subdomains": len(sanitized_subdomains)
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