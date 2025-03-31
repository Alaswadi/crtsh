from fastapi import APIRouter, Query, HTTPException
from app.services.subdomain_service import SubdomainService
from typing import Optional

router = APIRouter(
    prefix="/domains",
    tags=["domains"],
    responses={404: {"description": "Not found"}},
)

@router.get("/")
async def search_by_domain(
    domain: str = Query(..., description="The domain to search for subdomains"),
    use_cache: Optional[bool] = Query(True, description="Whether to use cached results if available")
):
    """
    Search for subdomains for a given domain using subfinder and crt.sh
    """
    if not domain:
        raise HTTPException(status_code=400, detail="Domain parameter is required")
    
    try:
        results = await SubdomainService.get_subdomains_by_domain(domain, use_cache)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.get("/clear-cache")
async def clear_domain_cache(
    domain: str = Query(..., description="The domain to clear cache for")
):
    """
    Clear the cache for a specific domain
    """
    from app.core.redis import delete_cache
    
    if not domain:
        raise HTTPException(status_code=400, detail="Domain parameter is required")
    
    try:
        await delete_cache(f"domain:{domain}")
        return {"message": f"Cache cleared for domain {domain}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}") 