import asyncio
import re
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

async def run_command_with_timeout(command: str, timeout: int = 60) -> Optional[str]:
    """
    Run a shell command with a timeout
    
    Args:
        command: The shell command to execute
        timeout: Timeout in seconds
        
    Returns:
        Command output or None if it fails/times out
    """
    try:
        logger.debug(f"Running command with timeout {timeout}s: {command}")
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=timeout
            )
            
            if process.returncode != 0:
                logger.error(f"Command failed with exit code {process.returncode}: {stderr.decode()}")
                return None
            
            return stdout.decode()
        except asyncio.TimeoutError:
            # Try to terminate the process
            logger.warning(f"Command timed out after {timeout}s: {command}")
            try:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                logger.warning(f"Process termination timed out, killing: {command}")
                process.kill()
            
            return None
    except Exception as e:
        logger.error(f"Error running command: {str(e)}")
        return None

def sanitize_domain(domain: str) -> str:
    """
    Sanitize a domain name to prevent command injection
    
    Args:
        domain: The domain name to sanitize
        
    Returns:
        Sanitized domain name
    """
    # Remove any protocol prefix (http://, https://, etc.)
    domain = re.sub(r'^https?://', '', domain)
    
    # Remove path, query string, and fragment
    domain = domain.split('/')[0].split('?')[0].split('#')[0]
    
    # Only allow alphanumeric characters, dots, and hyphens
    domain = re.sub(r'[^a-zA-Z0-9.-]', '', domain)
    
    # Make sure domain doesn't start with a dot or hyphen
    domain = domain.lstrip('.-')
    
    # Basic validation - domain must have at least one dot and no consecutive dots
    if '.' not in domain or '..' in domain:
        raise ValueError("Invalid domain format")
    
    return domain.lower() 