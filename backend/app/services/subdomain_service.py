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

class SubdomainService:
    @staticmethod
    async def get_subdomains_by_domain(domain: str, use_cache: bool = True):
        """Get subdomains for a given domain using subfinder and crt.sh"""
        cache_key = f"domain:{domain}"
        
        # Check cache first if enabled
        if use_cache:
            cached_data = await get_cache(cache_key)
            if cached_data:
                return cached_data
        
        # Create temporary directory for output files
        with tempfile.TemporaryDirectory() as temp_dir:
            subfinder_output = os.path.join(temp_dir, f"subfinder_{domain}.txt")
            crtsh_output = os.path.join(temp_dir, f"crtsh_{domain}.txt")
            combined_output = os.path.join(temp_dir, f"domain_{domain}.txt")
            
            # Run tasks concurrently
            with ThreadPoolExecutor(max_workers=settings.MAX_THREADS) as executor:
                futures = []
                futures.append(executor.submit(
                    SubdomainService._run_subfinder, domain, subfinder_output
                ))
                futures.append(executor.submit(
                    SubdomainService._run_crtsh, domain, crtsh_output
                ))
                
                # Wait for all tasks to complete
                for future in futures:
                    future.result()
                
                # Combine and deduplicate results
                subdomains = SubdomainService._combine_results(
                    subfinder_output, crtsh_output, combined_output
                )
                
                # Run httpx on the combined results with batching for large domains
                httpx_results = []
                
                # If we have a lot of subdomains, process them in batches
                if len(subdomains) > 100:
                    print(f"Large domain with {len(subdomains)} subdomains. Processing in batches...")
                    # Process in batches of 100 domains
                    batch_size = 100
                    num_batches = math.ceil(len(subdomains) / batch_size)
                    
                    # Process batches in parallel
                    with ThreadPoolExecutor(max_workers=min(num_batches, settings.MAX_THREADS)) as batch_executor:
                        batch_futures = []
                        
                        for i in range(num_batches):
                            start_idx = i * batch_size
                            end_idx = min(start_idx + batch_size, len(subdomains))
                            batch = subdomains[start_idx:end_idx]
                            
                            print(f"Submitting batch {i+1}/{num_batches} with {len(batch)} domains")
                            batch_futures.append(
                                batch_executor.submit(SubdomainService._run_httpx, batch)
                            )
                        
                        # Collect results from all batches
                        for future in batch_futures:
                            batch_results = future.result()
                            if batch_results:
                                httpx_results.extend(batch_results)
                else:
                    # For smaller domain counts, process all at once
                    httpx_results = SubdomainService._run_httpx(subdomains)
                
                # Prepare the result
                result = {
                    "domain": domain,
                    "subdomains": subdomains,
                    "httpx_results": httpx_results,
                    "total_subdomains": len(subdomains)
                }
                
                # Cache the result if enabled
                if use_cache:
                    await set_cache(cache_key, result)
                
                return result
    
    @staticmethod
    async def get_subdomains_by_organization(org_name: str, use_cache: bool = True):
        """Get subdomains for a given organization using crt.sh"""
        cache_key = f"org:{org_name}"
        
        # Check cache first if enabled
        if use_cache:
            cached_data = await get_cache(cache_key)
            if cached_data:
                return cached_data
        
        # Create temporary directory for output files
        with tempfile.TemporaryDirectory() as temp_dir:
            org_output = os.path.join(temp_dir, f"org_{org_name}.txt")
            
            # Run crt.sh for the organization
            domains = SubdomainService._run_crtsh_org(org_name, org_output)
            
            # Run httpx on the domains with batching for large organizations
            httpx_results = []
            
            # If we have a lot of domains, process them in batches
            if len(domains) > 100:
                print(f"Large organization with {len(domains)} domains. Processing in batches...")
                # Process in batches of 100 domains
                batch_size = 100
                num_batches = math.ceil(len(domains) / batch_size)
                
                # Process batches in parallel
                with ThreadPoolExecutor(max_workers=min(num_batches, settings.MAX_THREADS)) as batch_executor:
                    batch_futures = []
                    
                    for i in range(num_batches):
                        start_idx = i * batch_size
                        end_idx = min(start_idx + batch_size, len(domains))
                        batch = domains[start_idx:end_idx]
                        
                        print(f"Submitting batch {i+1}/{num_batches} with {len(batch)} domains")
                        batch_futures.append(
                            batch_executor.submit(SubdomainService._run_httpx, batch)
                        )
                    
                    # Collect results from all batches
                    for future in batch_futures:
                        batch_results = future.result()
                        if batch_results:
                            httpx_results.extend(batch_results)
            else:
                # For smaller domain counts, process all at once
                httpx_results = SubdomainService._run_httpx(domains)
            
            # Prepare the result
            result = {
                "organization": org_name,
                "domains": domains,
                "httpx_results": httpx_results,
                "total_domains": len(domains)
            }
            
            # Cache the result if enabled
            if use_cache:
                await set_cache(cache_key, result)
            
            return result
    
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
    
    @staticmethod
    def _run_httpx(domains):
        """Run httpx on a list of domains to get additional information"""
        if not domains:
            print("No domains provided to httpx")
            return []
        
        print(f"Processing {len(domains)} domains with httpx")
        
        # Create a temporary file with the domains
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
            for domain in domains:
                temp_file.write(f"{domain}\n")
            temp_file_path = temp_file.name
        
        try:
            # Use the explicitly linked pd-httpx command with timeouts
            cmd = [
                "pd-httpx", 
                "-l", temp_file_path,
                "-silent",
                "-timeout", "5",  # 5 second timeout per request
                "-rate-limit", "150",  # Rate limit for large scans
                "-retries", "1",  # Only retry once to avoid long waits
                "-tech-detect",
                "-status-code",
                "-json"
            ]
            
            print(f"Executing command: {' '.join(cmd)}")
            
            # Add timeout to process to prevent hanging
            process = subprocess.run(
                cmd, 
                check=False,
                timeout=120,  # 2 minutes timeout for the entire process
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Print stderr for debugging
            if process.stderr:
                print(f"HTTPX stderr: {process.stderr}")
            
            if process.returncode != 0:
                print(f"HTTPX exited with error code: {process.returncode}")
                # Try with full path to httpx
                cmd = [
                    "/root/go/bin/httpx", 
                    "-l", temp_file_path,
                    "-silent",
                    "-timeout", "5",
                    "-rate-limit", "150",
                    "-retries", "1",
                    "-json"
                ]
                print(f"Retrying with absolute path: {' '.join(cmd)}")
                process = subprocess.run(
                    cmd, 
                    check=False,
                    timeout=120,
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                if process.stderr:
                    print(f"HTTPX retry stderr: {process.stderr}")
            
            # Check if we have any output
            if not process.stdout:
                print("HTTPX did not produce any output")
                return []
                
            # Parse the JSON output
            results = []
            for line in process.stdout.splitlines():
                if line.strip():
                    try:
                        result = json.loads(line)
                        results.append(result)
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error: {e}, Line: {line}")
            
            print(f"HTTPX found {len(results)} results")
            return results
        except subprocess.TimeoutExpired:
            print("HTTPX process timed out")
            return []
        except Exception as e:
            import traceback
            print(f"Error running httpx: {e}")
            print(traceback.format_exc())
            return []
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path) 