# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV GUNICORN_BIND=0.0.0.0:5000
ENV GUNICORN_WORKER_CLASS=gthread

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    netcat-openbsd \
    curl \
    dnsutils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --default-timeout=100 -r requirements.txt

# Copy project
COPY . .

# Create necessary directories
RUN mkdir -p uploads instance

# Make entrypoint executable
RUN chmod +x docker-entrypoint.sh

# Expose port
EXPOSE 5000

# Set entrypoint
ENTRYPOINT ["./docker-entrypoint.sh"]

# Run gunicorn
CMD ["gunicorn", "--config", "gunicorn_config.py", "run:app"]
