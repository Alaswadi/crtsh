# Subdomain Finder

A modern web application for finding subdomains using subfinder, crt.sh, and httpx tools.

## Features

- Find subdomains for a given domain using both subfinder and crt.sh
- Search for domains registered by an organization using crt.sh
- Get detailed information about discovered domains using httpx
- Fast and multithreaded processing
- Redis caching for improved performance
- Modern UI built with React and Material UI
- Available via both FastAPI (Python) and PHP endpoints

## Architecture

The application consists of the following components:

- **FastAPI Backend**: Python-based backend with multithreading and Redis caching
- **PHP Backend**: Alternative PHP interface with the same functionality
- **React Frontend**: Modern UI for interacting with the API
- **Redis**: For caching results

## Requirements

- Docker and Docker Compose
- Internet connection

## Running the Application

1. Clone the repository:

```bash
git clone https://github.com/yourusername/subdomain-finder.git
cd subdomain-finder
```

2. Start the containers:

```bash
docker-compose up -d
```

3. Access the services:

- Frontend UI: http://localhost:8965
- FastAPI Backend: http://localhost:8963
- PHP Backend: http://localhost:8964

## API Endpoints

### FastAPI Endpoints

- GET `/api/domains?domain={domain_name}&use_cache={true|false}` - Search for subdomains
- GET `/api/organizations?org_name={organization_name}&use_cache={true|false}` - Search by organization
- GET `/health` - Health check endpoint

### PHP Endpoints

- GET `/api/domains?domain={domain_name}&use_cache={true|false}` - Search for subdomains
- GET `/api/organizations?org_name={organization_name}&use_cache={true|false}` - Search by organization
- GET `/health` - Health check endpoint

## Customizing

You can customize the following environment variables in the `docker-compose.yml` file:

- `MAX_THREADS`: Number of threads for concurrent processing (default: 10)
- `REDIS_HOST`: Redis host (default: redis)
- `REDIS_PORT`: Redis port (default: 6379)

## Tools Used

- **subfinder**: Fast subdomain discovery tool
- **crt.sh**: Certificate transparency logs search
- **httpx**: Fast HTTP probing with technology detection

## License

MIT 