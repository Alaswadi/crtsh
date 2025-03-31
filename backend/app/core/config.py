import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "Subdomain Finder API"
    
    # Redis settings
    REDIS_HOST: str = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    
    # Cache settings
    CACHE_EXPIRATION: int = 3600  # 1 hour
    
    # Multithreading settings
    MAX_THREADS: int = int(os.getenv("MAX_THREADS", 10))
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings() 