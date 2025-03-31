#!/usr/bin/env python3
import subprocess
import tempfile
import json
import os

def test_httpx():
    """Test if httpx is working correctly"""
    print("Starting httpx test...")
    
    # Test domains
    domains = ["google.com", "microsoft.com", "facebook.com"]
    
    # Create a temporary file with the domains
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
        for domain in domains:
            temp_file.write(f"{domain}\n")
        temp_file_path = temp_file.name
    
    try:
        # First, check both httpx locations
        try:
            print("Checking pd-httpx symlink:")
            pd_version_result = subprocess.run(
                ["pd-httpx", "-version"],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            print(f"pd-httpx version stdout: {pd_version_result.stdout}")
            print(f"pd-httpx version stderr: {pd_version_result.stderr}")
            
            print("\nChecking Go httpx at absolute path:")
            go_version_result = subprocess.run(
                ["/root/go/bin/httpx", "-version"],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            print(f"Go httpx version stdout: {go_version_result.stdout}")
            print(f"Go httpx version stderr: {go_version_result.stderr}")
            
            print("\nChecking httpx in PATH:")
            which_result = subprocess.run(
                ["which", "httpx"],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            print(f"Which httpx: {which_result.stdout}")
            
        except Exception as e:
            print(f"Error checking httpx versions: {e}")
        
        # Now test with pd-httpx
        cmd = [
            "pd-httpx",
            "-l", temp_file_path,
            "-silent",
            "-json"
        ]
        
        print(f"\nRunning command: {' '.join(cmd)}")
        
        process = subprocess.run(
            cmd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        if process.returncode != 0:
            print(f"pd-httpx exited with error code: {process.returncode}")
            print(f"Stderr: {process.stderr}")
            
            # Try with absolute path
            cmd = [
                "/root/go/bin/httpx",
                "-l", temp_file_path,
                "-silent",
                "-json"
            ]
            print(f"\nRetrying with absolute path: {' '.join(cmd)}")
            
            process = subprocess.run(
                cmd,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            if process.returncode != 0:
                print(f"Absolute path httpx exited with error code: {process.returncode}")
                print(f"Stderr: {process.stderr}")
                return False
        
        if not process.stdout:
            print("httpx did not produce any output")
            return False
        
        # Parse the JSON output
        results = []
        for line in process.stdout.splitlines():
            if line.strip():
                try:
                    result = json.loads(line)
                    results.append(result)
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}, Line: {line}")
        
        print(f"httpx found {len(results)} results:")
        for result in results:
            print(f"  - {result.get('url') or result.get('host')} (Status: {result.get('status_code')})")
        
        return len(results) > 0
    
    except Exception as e:
        import traceback
        print(f"Error during test: {e}")
        print(traceback.format_exc())
        return False
    
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

if __name__ == "__main__":
    if test_httpx():
        print("✅ httpx test passed!")
    else:
        print("❌ httpx test failed!") 