<?php
class RedisService {
    private $redis;
    
    public function __construct() {
        $this->connect();
    }
    
    /**
     * Connect to Redis server
     * 
     * @return void
     */
    private function connect() {
        try {
            $this->redis = new Redis();
            $this->redis->connect(REDIS_HOST, REDIS_PORT);
        } catch (Exception $e) {
            // Handle connection error gracefully, but don't stop execution
            error_log("Redis connection error: " . $e->getMessage());
            $this->redis = null;
        }
    }
    
    /**
     * Get value from cache
     * 
     * @param string $key The cache key
     * @return mixed The cached value or null if not found
     */
    public function get($key) {
        if (!$this->redis) {
            return null;
        }
        
        try {
            $value = $this->redis->get($key);
            return $value ? json_decode($value, true) : null;
        } catch (Exception $e) {
            error_log("Redis get error: " . $e->getMessage());
            return null;
        }
    }
    
    /**
     * Set value in cache
     * 
     * @param string $key The cache key
     * @param mixed $value The value to cache
     * @param int $expiration The expiration time in seconds
     * @return bool Whether the operation was successful
     */
    public function set($key, $value, $expiration = CACHE_EXPIRATION) {
        if (!$this->redis) {
            return false;
        }
        
        try {
            return $this->redis->setex($key, $expiration, json_encode($value));
        } catch (Exception $e) {
            error_log("Redis set error: " . $e->getMessage());
            return false;
        }
    }
    
    /**
     * Delete a key from cache
     * 
     * @param string $key The cache key to delete
     * @return bool Whether the operation was successful
     */
    public function delete($key) {
        if (!$this->redis) {
            return false;
        }
        
        try {
            return $this->redis->del($key) > 0;
        } catch (Exception $e) {
            error_log("Redis delete error: " . $e->getMessage());
            return false;
        }
    }
    
    /**
     * Check if Redis is available
     * 
     * @return bool Whether Redis is available
     */
    public function isAvailable() {
        if (!$this->redis) {
            return false;
        }
        
        try {
            return $this->redis->ping() === '+PONG';
        } catch (Exception $e) {
            return false;
        }
    }
} 