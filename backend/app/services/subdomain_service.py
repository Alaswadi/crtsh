import os
import json
import asyncio
import tempfile
import subprocess
from concurrent.futures import ThreadPoolExecutor
import httpx
import math
from app.core.config import settings
from app.core.redis import get_cache, set_cache
from app.utils.command_utils import run_command_with_timeout, sanitize_domain
import time
import logging
from typing import List, Dict, Any, Optional
import traceback

logger = logging.getLogger(__name__)

class SubdomainService:
    @staticmethod
    async def get_subdomains_by_domain(domain: str, use_cache: bool = True, run_httpx: bool = True) -> Dict[str, Any]:
        """
        Get subdomains for a domain using subfinder and crt.sh
        
        Args:
            domain: The domain to search for
            use_cache: Whether to use cached results
            run_httpx: Whether to run httpx after collecting subdomains
            
        Returns:
            Dictionary with subdomains and httpx results
        """
        domain = sanitize_domain(domain)
        
        # Check cache first
        if use_cache:
            cache_key = f"domain:{domain}"
            cached_data = await get_cache(cache_key)
            if cached_data:
                return cached_data
        
        # Get subdomains from crt.sh and subfinder
        start_time = time.time()
        crtsh_subdomains = await SubdomainService._get_crtsh_subdomains(domain)
        subfinder_subdomains = await SubdomainService._get_subfinder_subdomains(domain)
        
        # Create a new list with combined subdomains - avoid modifying the original lists
        combined_subdomains = crtsh_subdomains.copy() if crtsh_subdomains else []
        if subfinder_subdomains:
            combined_subdomains.extend(subfinder_subdomains)
        
        # Remove duplicates using a set and convert back to list
        all_subdomains = list(set(combined_subdomains))
        
        # Prepare the initial result without httpx
        result = {
            "domain": domain,
            "source": "subfinder + crt.sh",
            "total_subdomains": len(all_subdomains),
            "subdomains": all_subdomains,
            "httpx_results": [],
            "httpx_status": "not_started" if not run_httpx else "running",
            "execution_time": round(time.time() - start_time, 2)
        }
        
        # Save to cache immediately to give quick results
        cache_key = f"domain:{domain}"
        await set_cache(cache_key, result)
        
        # Run httpx if requested
        if run_httpx:
            try:
                # Create a new list copy to ensure it's not modified during the async operation
                subdomains_copy = all_subdomains.copy()
                
                # Update the result with httpx data
                httpx_result = await SubdomainService.run_httpx_for_domain(domain, subdomains_copy)
                if httpx_result:
                    result.update(httpx_result)
                result["execution_time"] = round(time.time() - start_time, 2)
                
                # Update cache with httpx results
                await set_cache(cache_key, result)
            except Exception as e:
                logger.error(f"Error running httpx for domain {domain}: {str(e)}")
                # Update the httpx status in the result and cache
                result["httpx_status"] = "error"
                result["httpx_error"] = str(e)
                await set_cache(cache_key, result)
        
        return result
    
    @staticmethod
    async def run_httpx_for_domain(domain: str, subdomains: List[str]) -> Dict[str, Any]:
        """Run httpx scan on subdomains of a domain"""
        try:
            logger.info(f"Starting HTTPX scan for domain: {domain}")
            logger.info(f"Number of subdomains to scan: {len(subdomains)}")
            
            # Check if httpx is installed
            try:
                check_cmd = ["/root/go/bin/httpx", "-version"]
                process = await asyncio.create_subprocess_exec(
                    *check_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                if process.returncode != 0:
                    logger.error(f"HTTPX is not properly installed. Version check failed: {stderr.decode()}")
                    raise Exception("HTTPX is not properly installed")
                logger.info(f"HTTPX version: {stdout.decode().strip()}")
            except Exception as e:
                logger.error(f"Failed to check HTTPX installation: {str(e)}")
                raise Exception("HTTPX is not properly installed or accessible")
            
            # Make a safe copy of the list
            subdomains_copy = list(subdomains)
            logger.info(f"Created safe copy of subdomains list with {len(subdomains_copy)} entries")
            
            # Process in batches of 50
            batch_size = 50
            httpx_results = []
            total_batches = (len(subdomains_copy) + batch_size - 1) // batch_size
            
            logger.info(f"Will process {total_batches} batches of {batch_size} subdomains each")
            
            for i in range(0, len(subdomains_copy), batch_size):
                batch = subdomains_copy[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                logger.info(f"Processing batch {batch_num}/{total_batches} with {len(batch)} subdomains")
                
                # Create a temporary file for the batch
                with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                    for subdomain in batch:
                        f.write(f"{subdomain}\n")
                    temp_file = f.name
                
                logger.info(f"Created temporary file: {temp_file}")
                
                try:
                    # Run httpx with the temporary file
                    logger.info(f"Running httpx command for batch {batch_num}")
                    cmd = [
                        "/root/go/bin/httpx",
                        "-l", temp_file,
                        "-silent",
                        "-json",
                        "-title",
                        "-status-code",
                        "-content-length",
                        "-no-color",
                        "-timeout", "10",
                        "-retries", "2",
                        "-threads", "50",
                        "-rate-limit", "100",
                        "-verbose"  # Add verbose flag for more detailed output
                    ]
                    
                    logger.info(f"HTTPX command: {' '.join(cmd)}")
                    
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    stdout, stderr = await process.communicate()
                    
                    if process.returncode != 0:
                        error_msg = stderr.decode() if stderr else "No error message available"
                        logger.error(f"HTTPX command failed with exit code {process.returncode}")
                        logger.error(f"HTTPX stderr: {error_msg}")
                        logger.error(f"HTTPX stdout: {stdout.decode() if stdout else 'No output'}")
                        raise Exception(f"HTTPX command failed: {error_msg}")
                    
                    # Parse the JSON output
                    logger.info(f"Successfully ran HTTPX for batch {batch_num}")
                    for line in stdout.decode().splitlines():
                        if line.strip():
                            try:
                                result = json.loads(line)
                                httpx_results.append(result)
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to parse JSON line: {line}")
                                logger.error(f"JSON decode error: {str(e)}")
                                continue
                    
                    logger.info(f"Processed {len(httpx_results)} results in batch {batch_num}")
                    
                except Exception as e:
                    logger.error(f"Error processing batch {batch_num}: {str(e)}")
                    logger.error(f"Batch subdomains: {batch}")
                    raise
                finally:
                    # Clean up the temporary file
                    try:
                        os.unlink(temp_file)
                        logger.info(f"Cleaned up temporary file: {temp_file}")
                    except Exception as e:
                        logger.error(f"Failed to delete temporary file {temp_file}: {str(e)}")
            
            logger.info(f"Completed HTTPX scan for {domain}. Total results: {len(httpx_results)}")
            
            return {
                "httpx_status": "completed",
                "httpx_results": httpx_results
            }
            
        except Exception as e:
            logger.error(f"Error in run_httpx_for_domain for {domain}: {str(e)}")
            logger.error(f"Full error details: {traceback.format_exc()}")
            return {
                "httpx_status": "error",
                "httpx_error": str(e)
            }
    
    @staticmethod
    async def get_subdomains_by_organization(org_name: str, use_cache: bool = True, run_httpx: bool = True) -> Dict[str, Any]:
        """
        Get subdomains for an organization from crt.sh
        
        Args:
            org_name: The organization name to search for
            use_cache: Whether to use cached results
            run_httpx: Whether to run httpx after collecting subdomains
            
        Returns:
            Dictionary with domains, subdomains and httpx results
        """
        # Check cache first
        if use_cache:
            cache_key = f"org:{org_name}"
            cached_data = await get_cache(cache_key)
            if cached_data:
                return cached_data
        
        # Get domains from crt.sh
        start_time = time.time()
        crtsh_result = await SubdomainService._get_crtsh_by_organization(org_name)
        
        # If we have domains, get subdomains for each domain
        all_domains = []
        all_subdomains = []
        
        if crtsh_result:
            domains = crtsh_result.get("domains", []).copy()  # Make a copy of domains list
            
            # Limit to first 10 domains to avoid overloading
            domains = domains[:10]
            
            # Process each domain
            for domain in domains:
                try:
                    # Get subdomains but don't run httpx yet
                    domain_result = await SubdomainService.get_subdomains_by_domain(domain, use_cache, run_httpx=False)
                    all_domains.append({
                        "domain": domain,
                        "total_subdomains": domain_result.get("total_subdomains", 0)
                    })
                    # Extend the all_subdomains list with a copy of the domain's subdomains
                    domain_subdomains = domain_result.get("subdomains", [])
                    if domain_subdomains:
                        all_subdomains.extend(domain_subdomains.copy())
                except Exception as e:
                    logger.error(f"Error getting subdomains for {domain}: {str(e)}")
        
        # Remove duplicates by creating a new list from a set
        all_subdomains = list(set(all_subdomains))
        
        # Prepare the initial result without httpx
        result = {
            "organization": org_name,
            "total_domains": len(all_domains),
            "domains": all_domains,
            "total_subdomains": len(all_subdomains),
            "subdomains": all_subdomains,
            "httpx_results": [],
            "httpx_status": "not_started" if not run_httpx else "running",
            "execution_time": round(time.time() - start_time, 2)
        }
        
        # Save to cache immediately
        cache_key = f"org:{org_name}"
        await set_cache(cache_key, result)
        
        # Run httpx if requested
        if run_httpx and all_subdomains:
            try:
                # Create a new copy of the all_subdomains list for httpx
                subdomains_copy = all_subdomains.copy()
                
                # Update with httpx results
                httpx_result = await SubdomainService._run_httpx(subdomains_copy)
                if httpx_result:
                    result["httpx_results"] = httpx_result
                result["httpx_status"] = "completed"
                result["execution_time"] = round(time.time() - start_time, 2)
                
                # Update cache
                await set_cache(cache_key, result)
            except Exception as e:
                logger.error(f"Error running httpx for organization {org_name}: {str(e)}")
                result["httpx_status"] = "error"
                result["httpx_error"] = str(e)
                await set_cache(cache_key, result)
        
        return result
    
    @staticmethod
    async def _get_crtsh_subdomains(domain: str) -> List[str]:
        """Get subdomains for a domain from crt.sh"""
        try:
            command = f"curl -s 'https://crt.sh/?q=%25.{domain}&output=json' | jq -r '.[].name_value' | sort -u"
            result = await run_command_with_timeout(command, timeout=30)
            
            subdomains = []
            if result:
                # Process lines into subdomains
                subdomains = result.strip().split("\n")
                
                # Remove duplicates and filter valid subdomains
                subdomains = [s for s in set(subdomains) if s and "*" not in s]
            
            return subdomains
        except Exception as e:
            logger.error(f"Error getting crt.sh subdomains: {str(e)}")
            return []
    
    @staticmethod
    async def _get_subfinder_subdomains(domain: str) -> List[str]:
        """Get subdomains for a domain using subfinder"""
        try:
            command = f"subfinder -d {domain} -silent"
            result = await run_command_with_timeout(command, timeout=120)  # 2 minute timeout
            
            subdomains = []
            if result:
                # Process lines into subdomains
                subdomains = result.strip().split("\n")
                
                # Remove duplicates and filter valid subdomains
                subdomains = [s for s in set(subdomains) if s]
            
            return subdomains
        except Exception as e:
            logger.error(f"Error getting subfinder subdomains: {str(e)}")
            return []
    
    @staticmethod
    async def _run_httpx(domains: List[str]) -> List[Dict[str, Any]]:
        """
        Run httpx on a list of domains to get HTTP information
        
        Args:
            domains: List of domains to scan
            
        Returns:
            List of httpx results
        """
        if not domains:
            logger.info("No domains provided to _run_httpx")
            return []
        
        try:
            # Create a completely sanitized list with explicit string conversion
            sanitized_domains = []
            for domain in domains:
                if domain:  # Skip empty entries
                    sanitized_domains.append(str(domain))
            
            logger.info(f"Running httpx on {len(sanitized_domains)} sanitized domains")
            
            # Write domains to temporary file
            temp_file = "/tmp/domains.txt"
            with open(temp_file, "w") as f:
                for domain in sanitized_domains:
                    f.write(f"{domain}\n")
            
            # Run httpx with reasonable timeout and concurrency
            # -silent: Don't print the banner
            # -title: Extract title
            # -status-code: Extract status code
            # -content-length: Extract content length
            # -threads: Number of threads
            # -rate-limit: Rate limit
            # -timeout: Timeout in seconds
            command = f"cat {temp_file} | httpx -silent -title -status-code -content-length -threads 50 -rate-limit 150 -timeout 5 -json"
            result = await run_command_with_timeout(command, timeout=300)  # 5 minute timeout
            
            # Process results
            httpx_results = []
            if result:
                # Split by newline and parse each JSON object
                for line in result.strip().split("\n"):
                    try:
                        if line:
                            data = json.loads(line)
                            httpx_results.append(data)
                    except json.JSONDecodeError:
                        logger.error(f"Error parsing httpx JSON: {line}")
            
            # Clean up temp file
            try:
                os.remove(temp_file)
            except Exception as e:
                logger.error(f"Error removing temp file: {str(e)}")
            
            logger.info(f"HTTPX completed successfully with {len(httpx_results)} results")
            return httpx_results
        except Exception as e:
            logger.error(f"Error running httpx: {str(e)}")
            # Ensure we return a list even on error
            return []
    
    @staticmethod
    async def _get_crtsh_by_organization(org_name: str) -> Dict[str, Any]:
        """Get domains for an organization from crt.sh"""
        try:
            # Escape spaces and special characters
            org_name_escaped = org_name.replace(" ", "+").replace("&", "%26")
            
            command = f"curl -s 'https://crt.sh/?o={org_name_escaped}&output=json' | jq -r '.[] | .name_value' | sort -u"
            result = await run_command_with_timeout(command, timeout=60)
            
            domains = []
            if result:
                # Process lines and extract unique root domains
                all_domains = result.strip().split("\n")
                
                # Extract root domains
                root_domains = set()
                for domain in all_domains:
                    parts = domain.split(".")
                    if len(parts) > 1:
                        # Take last two parts for domains like example.com
                        # But handle special cases like co.uk where we need three parts
                        if parts[-2] in ["co", "com", "org", "net", "gov", "edu"] and parts[-1] in ["uk", "au", "nz", "za"]:
                            if len(parts) > 2:
                                root_domain = ".".join(parts[-3:])
                                root_domains.add(root_domain)
                        else:
                            root_domain = ".".join(parts[-2:])
                            root_domains.add(root_domain)
                
                domains = list(root_domains)
            
            return {
                "organization": org_name,
                "total_domains": len(domains),
                "domains": domains
            }
        except Exception as e:
            logger.error(f"Error getting crt.sh organization domains: {str(e)}")
            return {"organization": org_name, "total_domains": 0, "domains": []}
    
    @staticmethod
    def _run_subfinder(domain, output_file):
        """Run subfinder to find subdomains"""
        cmd = ["subfinder", "-d", domain, "-o", output_file, "-silent"]
        try:
            # Add timeout to prevent hanging
            subprocess.run(cmd, check=True, timeout=120)
        except subprocess.TimeoutExpired:
            print(f"Subfinder timed out for domain {domain}")
        
        # Return subdomains as a list if the file exists
        if os.path.exists(output_file):
            with open(output_file, 'r') as f:
                return [line.strip() for line in f if line.strip()]
        return []
    
    @staticmethod
    def _run_crtsh(domain, output_file):
        """Get subdomains from crt.sh"""
        url = f"https://crt.sh/?q=%.{domain}&output=json"
        try:
            with httpx.Client(timeout=30.0) as client:  # Add timeout
                response = client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    
                    # Extract and clean subdomains
                    subdomains = set()
                    for entry in data:
                        for field in ['common_name', 'name_value']:
                            if field in entry:
                                # Process each subdomain
                                for subdomain in entry[field].split('\\n'):
                                    subdomain = subdomain.strip()
                                    # Remove wildcards and filter out email addresses
                                    if subdomain.startswith('*.'):
                                        subdomain = subdomain[2:]
                                    if '@' not in subdomain:
                                        subdomains.add(subdomain)
                    
                    # Write to output file
                    with open(output_file, 'w') as f:
                        for subdomain in sorted(subdomains):
                            f.write(f"{subdomain}\n")
                    
                    return list(subdomains)
        except Exception as e:
            print(f"Error fetching data from crt.sh: {e}")
        return []
    
    @staticmethod
    def _run_crtsh_org(org_name, output_file):
        """Get domains from crt.sh for an organization"""
        url = f"https://crt.sh/?q={org_name}&output=json"
        try:
            with httpx.Client(timeout=30.0) as client:  # Add timeout
                response = client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    
                    # Extract and clean domains
                    domains = set()
                    for entry in data:
                        if 'common_name' in entry:
                            domain = entry['common_name'].strip()
                            # Remove wildcards and filter out email addresses
                            if domain.startswith('*.'):
                                domain = domain[2:]
                            if '@' not in domain:
                                domains.add(domain)
                    
                    # Write to output file
                    with open(output_file, 'w') as f:
                        for domain in sorted(domains):
                            f.write(f"{domain}\n")
                    
                    return list(domains)
        except Exception as e:
            print(f"Error fetching data from crt.sh: {e}")
        return []
    
    @staticmethod
    def _combine_results(subfinder_output, crtsh_output, combined_output):
        """Combine and deduplicate results from subfinder and crt.sh"""
        combined_domains = set()
        
        # Add subfinder results
        if os.path.exists(subfinder_output):
            with open(subfinder_output, 'r') as f:
                for line in f:
                    domain = line.strip()
                    if domain:
                        combined_domains.add(domain)
        
        # Add crt.sh results
        if os.path.exists(crtsh_output):
            with open(crtsh_output, 'r') as f:
                for line in f:
                    domain = line.strip()
                    if domain:
                        combined_domains.add(domain)
        
        # Write combined results to file
        with open(combined_output, 'w') as f:
            for domain in sorted(combined_domains):
                f.write(f"{domain}\n")
        
        return sorted(list(combined_domains)) 