FROM python:3.11-slim

# Build arguments
ARG API_VERSION=1.0.0

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV API_VERSION=${API_VERSION}

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        default-libmysqlclient-dev \
        pkg-config \
        netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Make startup scripts executable
RUN chmod +x /app/scripts/start.sh /app/scripts/migrate.sh

# Expose port
EXPOSE 8000

# Run the application using the startup script with bash to ensure permissions
CMD ["bash", "/app/scripts/start.sh"]
