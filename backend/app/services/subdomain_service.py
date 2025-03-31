import os
import json
import asyncio
import tempfile
import subprocess
from concurrent.futures import ThreadPoolExecutor
import httpx
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
                
                # Run httpx on the combined results
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
            
            # Run httpx on the domains
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
        subprocess.run(cmd, check=True)
        
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
            with httpx.Client() as client:
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
            with httpx.Client() as client:
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
            return []
        
        # Create a temporary file with the domains
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
            for domain in domains:
                temp_file.write(f"{domain}\n")
            temp_file_path = temp_file.name
        
        try:
            # Run httpx command
            cmd = [
                "httpx", 
                "-l", temp_file_path,
                "-silent",
                "-tech-detect",
                "-status-code",
                "-json"
            ]
            
            process = subprocess.run(
                cmd, 
                check=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Parse the JSON output
            results = []
            for line in process.stdout.splitlines():
                if line.strip():
                    try:
                        result = json.loads(line)
                        results.append(result)
                    except json.JSONDecodeError:
                        pass
            
            return results
        except Exception as e:
            print(f"Error running httpx: {e}")
            return []
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path) 