from fastapi import APIRouter, Query, HTTPException
from app.services.subdomain_service import SubdomainService
from typing import Optional

router = APIRouter(
    prefix="/organizations",
    tags=["organizations"],
    responses={404: {"description": "Not found"}},
)

@router.get("/")
async def search_by_organization(
    org_name: str = Query(..., description="The organization name to search for domains"),
    use_cache: Optional[bool] = Query(True, description="Whether to use cached results if available")
):
    """
    Search for domains registered by an organization using crt.sh
    """
    if not org_name:
        raise HTTPException(status_code=400, detail="Organization name parameter is required")
    
    try:
        results = await SubdomainService.get_subdomains_by_organization(org_name, use_cache)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.get("/clear-cache")
async def clear_organization_cache(
    org_name: str = Query(..., description="The organization name to clear cache for")
):
    """
    Clear the cache for a specific organization
    """
    from app.core.redis import delete_cache
    
    if not org_name:
        raise HTTPException(status_code=400, detail="Organization name parameter is required")
    
    try:
        await delete_cache(f"org:{org_name}")
        return {"message": f"Cache cleared for organization {org_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}") 