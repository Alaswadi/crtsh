FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    jq \
    git \
    wget \
    iputils-ping \
    dnsutils \
    dos2unix \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Go for subfinder and httpx
RUN wget https://golang.org/dl/go1.21.6.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go1.21.6.linux-amd64.tar.gz && \
    rm go1.21.6.linux-amd64.tar.gz

# Set up Go environment
ENV PATH=$PATH:/usr/local/go/bin:/root/go/bin
ENV GOROOT=/usr/local/go
ENV GOPATH=/root/go

# Install subfinder and httpx
RUN go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest && \
    go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest

# Verify the tools are installed correctly
RUN echo "Go path: $PATH" && \
    subfinder -version && \
    /root/go/bin/httpx -version && \
    echo "Which httpx: $(which httpx)" && \
    ln -sf /root/go/bin/httpx /usr/local/bin/pd-httpx

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create output directory
RUN mkdir -p output

# Fix line endings and make the entrypoint script executable
RUN dos2unix entrypoint.sh && \
    chmod +x entrypoint.sh && \
    ls -la entrypoint.sh

# Use the entrypoint script
ENTRYPOINT ["/bin/bash", "./entrypoint.sh"] 