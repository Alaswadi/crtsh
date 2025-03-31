<?php
require_once 'RedisService.php';

class SubdomainService {
    private $redisService;
    
    public function __construct() {
        $this->redisService = new RedisService();
    }
    
    /**
     * Get subdomains for a domain using subfinder and crt.sh
     * 
     * @param string $domain The domain to search for
     * @param bool $useCache Whether to use cached results
     * @return array The results
     */
    public function getSubdomainsByDomain($domain, $useCache = true) {
        // Check cache first if enabled
        $cacheKey = "domain:{$domain}";
        if ($useCache) {
            $cachedData = $this->redisService->get($cacheKey);
            if ($cachedData) {
                return $cachedData;
            }
        }
        
        // Create unique temporary files
        $tempId = uniqid();
        $subfinderOutput = TEMP_DIR . "/subfinder_{$domain}_{$tempId}.txt";
        $crtshOutput = TEMP_DIR . "/crtsh_{$domain}_{$tempId}.txt";
        $combinedOutput = TEMP_DIR . "/domain_{$domain}_{$tempId}.txt";
        
        try {
            // Run subfinder and crt.sh in parallel using background processes
            $this->runSubfinder($domain, $subfinderOutput);
            $this->runCrtsh($domain, $crtshOutput);
            
            // Wait for processes to complete
            $this->waitForFiles([$subfinderOutput, $crtshOutput], 30);
            
            // Combine results
            $subdomains = $this->combineResults($subfinderOutput, $crtshOutput, $combinedOutput);
            
            // Run httpx on the combined results
            $httpxResults = $this->runHttpx($subdomains);
            
            // Prepare result
            $result = [
                'domain' => $domain,
                'subdomains' => $subdomains,
                'httpx_results' => $httpxResults,
                'total_subdomains' => count($subdomains)
            ];
            
            // Cache the result if enabled
            if ($useCache) {
                $this->redisService->set($cacheKey, $result, CACHE_EXPIRATION);
            }
            
            // Clean up
            $this->cleanupFiles([$subfinderOutput, $crtshOutput, $combinedOutput]);
            
            return $result;
        } catch (Exception $e) {
            // Clean up on error
            $this->cleanupFiles([$subfinderOutput, $crtshOutput, $combinedOutput]);
            throw $e;
        }
    }
    
    /**
     * Get domains for an organization using crt.sh
     * 
     * @param string $orgName The organization name to search for
     * @param bool $useCache Whether to use cached results
     * @return array The results
     */
    public function getSubdomainsByOrganization($orgName, $useCache = true) {
        // Check cache first if enabled
        $cacheKey = "org:{$orgName}";
        if ($useCache) {
            $cachedData = $this->redisService->get($cacheKey);
            if ($cachedData) {
                return $cachedData;
            }
        }
        
        // Create unique temporary file
        $tempId = uniqid();
        $orgOutput = TEMP_DIR . "/org_{$orgName}_{$tempId}.txt";
        
        try {
            // Run crt.sh for the organization
            $domains = $this->runCrtshOrg($orgName, $orgOutput);
            
            // Run httpx on the domains
            $httpxResults = $this->runHttpx($domains);
            
            // Prepare result
            $result = [
                'organization' => $orgName,
                'domains' => $domains,
                'httpx_results' => $httpxResults,
                'total_domains' => count($domains)
            ];
            
            // Cache the result if enabled
            if ($useCache) {
                $this->redisService->set($cacheKey, $result, CACHE_EXPIRATION);
            }
            
            // Clean up
            $this->cleanupFiles([$orgOutput]);
            
            return $result;
        } catch (Exception $e) {
            // Clean up on error
            $this->cleanupFiles([$orgOutput]);
            throw $e;
        }
    }
    
    /**
     * Run subfinder to find subdomains
     * 
     * @param string $domain The domain to search for
     * @param string $outputFile The output file path
     * @return void
     */
    private function runSubfinder($domain, $outputFile) {
        $cmd = "subfinder -d {$domain} -o {$outputFile} -silent > /dev/null 2>&1 &";
        exec($cmd);
    }
    
    /**
     * Get subdomains from crt.sh
     * 
     * @param string $domain The domain to search for
     * @param string $outputFile The output file path
     * @return void
     */
    private function runCrtsh($domain, $outputFile) {
        $url = "https://crt.sh/?q=%.{$domain}&output=json";
        $cmd = "curl -s '{$url}' | jq '.[].common_name,.[].name_value' | tr -d '\"' | sed 's/\\\\n/\\n/g' | sed 's/\\*\\.//g' | grep -v '@' | sort | uniq > {$outputFile} 2>/dev/null &";
        exec($cmd);
    }
    
    /**
     * Get domains from crt.sh for an organization
     * 
     * @param string $orgName The organization name to search for
     * @param string $outputFile The output file path
     * @return array The domains
     */
    private function runCrtshOrg($orgName, $outputFile) {
        $url = "https://crt.sh/?q={$orgName}&output=json";
        $cmd = "curl -s '{$url}' | jq '.[].common_name' | tr -d '\"' | sed 's/\\\\n/\\n/g' | sed 's/\\*\\.//g' | grep -v '@' | sort | uniq > {$outputFile}";
        exec($cmd);
        
        // Wait for the command to complete
        $this->waitForFiles([$outputFile], 30);
        
        // Read the domains from the output file
        if (file_exists($outputFile)) {
            return array_filter(array_map('trim', file($outputFile)));
        }
        return [];
    }
    
    /**
     * Combine and deduplicate results from subfinder and crt.sh
     * 
     * @param string $subfinderOutput The subfinder output file path
     * @param string $crtshOutput The crt.sh output file path
     * @param string $combinedOutput The combined output file path
     * @return array The combined subdomains
     */
    private function combineResults($subfinderOutput, $crtshOutput, $combinedOutput) {
        $combinedDomains = [];
        
        // Add subfinder results
        if (file_exists($subfinderOutput)) {
            $subfinderDomains = array_filter(array_map('trim', file($subfinderOutput)));
            $combinedDomains = array_merge($combinedDomains, $subfinderDomains);
        }
        
        // Add crt.sh results
        if (file_exists($crtshOutput)) {
            $crtshDomains = array_filter(array_map('trim', file($crtshOutput)));
            $combinedDomains = array_merge($combinedDomains, $crtshDomains);
        }
        
        // Deduplicate and sort
        $combinedDomains = array_unique($combinedDomains);
        sort($combinedDomains);
        
        // Write combined results to file
        file_put_contents($combinedOutput, implode(PHP_EOL, $combinedDomains));
        
        return $combinedDomains;
    }
    
    /**
     * Run httpx on a list of domains to get additional information
     * 
     * @param array $domains The domains to scan
     * @return array The httpx results
     */
    private function runHttpx($domains) {
        if (empty($domains)) {
            return [];
        }
        
        // Create a temporary file with the domains
        $tempFile = TEMP_DIR . '/httpx_domains_' . uniqid() . '.txt';
        file_put_contents($tempFile, implode(PHP_EOL, $domains));
        
        // Run httpx command
        $cmd = "httpx -l {$tempFile} -silent -tech-detect -status-code -json";
        exec($cmd, $output);
        
        // Parse the JSON output
        $results = [];
        foreach ($output as $line) {
            if (trim($line)) {
                try {
                    $result = json_decode($line, true);
                    if ($result) {
                        $results[] = $result;
                    }
                } catch (Exception $e) {
                    // Skip invalid JSON
                }
            }
        }
        
        // Clean up the temporary file
        unlink($tempFile);
        
        return $results;
    }
    
    /**
     * Wait for files to be created with a timeout
     * 
     * @param array $files The files to wait for
     * @param int $timeoutSeconds The timeout in seconds
     * @return void
     */
    private function waitForFiles($files, $timeoutSeconds) {
        $start = time();
        $filesExist = false;
        
        while (time() - $start < $timeoutSeconds && !$filesExist) {
            $filesExist = true;
            
            foreach ($files as $file) {
                if (!file_exists($file)) {
                    $filesExist = false;
                    break;
                }
            }
            
            if (!$filesExist) {
                sleep(1);
            }
        }
    }
    
    /**
     * Clean up temporary files
     * 
     * @param array $files The files to clean up
     * @return void
     */
    private function cleanupFiles($files) {
        foreach ($files as $file) {
            if (file_exists($file)) {
                unlink($file);
            }
        }
    }
} 