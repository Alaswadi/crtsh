<?php
// Set the content type to JSON
header('Content-Type: application/json');

// Enable error reporting for development
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

// Required configuration
require_once 'config.php';

// Parse the request URL
$request_uri = $_SERVER['REQUEST_URI'];
$path = parse_url($request_uri, PHP_URL_PATH);
$segments = explode('/', trim($path, '/'));

// Get query parameters
$query_params = $_GET;

// Simple routing
$controller = isset($segments[0]) ? $segments[0] : 'home';
$action = isset($segments[1]) ? $segments[1] : 'index';

try {
    // Route the request
    switch ($controller) {
        case 'api':
            if ($action === 'domains') {
                // Handle domain search
                if (!isset($query_params['domain'])) {
                    http_response_code(400);
                    echo json_encode(["error" => "Domain parameter is required"]);
                    exit;
                }
                
                $domain = $query_params['domain'];
                $use_cache = isset($query_params['use_cache']) ? filter_var($query_params['use_cache'], FILTER_VALIDATE_BOOLEAN) : true;
                
                include_once 'services/SubdomainService.php';
                $service = new SubdomainService();
                $result = $service->getSubdomainsByDomain($domain, $use_cache);
                
                echo json_encode($result);
            } elseif ($action === 'organizations') {
                // Handle organization search
                if (!isset($query_params['org_name'])) {
                    http_response_code(400);
                    echo json_encode(["error" => "Organization name parameter is required"]);
                    exit;
                }
                
                $org_name = $query_params['org_name'];
                $use_cache = isset($query_params['use_cache']) ? filter_var($query_params['use_cache'], FILTER_VALIDATE_BOOLEAN) : true;
                
                include_once 'services/SubdomainService.php';
                $service = new SubdomainService();
                $result = $service->getSubdomainsByOrganization($org_name, $use_cache);
                
                echo json_encode($result);
            } elseif ($action === 'health') {
                // Handle health check
                include_once 'services/HealthService.php';
                $service = new HealthService();
                $result = $service->getHealthStatus();
                
                echo json_encode($result);
            } else {
                http_response_code(404);
                echo json_encode(["error" => "Endpoint not found"]);
            }
            break;
        
        case 'health':
            // Health check endpoint
            include_once 'services/HealthService.php';
            $service = new HealthService();
            $result = $service->getHealthStatus();
            
            echo json_encode($result);
            break;
        
        default:
            // API documentation or default response
            echo json_encode([
                "name" => "Subdomain Finder API (PHP)",
                "version" => "2.0",
                "endpoints" => [
                    "/api/domains?domain={domain_name}" => "Search for subdomains for a given domain",
                    "/api/organizations?org_name={organization_name}" => "Search for domains registered by an organization",
                    "/api/health" => "Check the health status of the API",
                    "/health" => "Alias for /api/health"
                ]
            ]);
    }
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(["error" => $e->getMessage()]);
}
?> 