<?php
// Configuration settings

// Redis connection
define('REDIS_HOST', getenv('REDIS_HOST') ?: 'redis');
define('REDIS_PORT', getenv('REDIS_PORT') ?: 6379);

// Cache settings
define('CACHE_EXPIRATION', 3600); // 1 hour

// Multithreading/concurrency settings
define('MAX_THREADS', getenv('MAX_THREADS') ?: 10);

// Temporary directory for output files
define('TEMP_DIR', sys_get_temp_dir() . '/subdomain-finder');

// Create temporary directory if it doesn't exist
if (!file_exists(TEMP_DIR)) {
    mkdir(TEMP_DIR, 0777, true);
}
?> 