FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and pyproject.toml for better caching
COPY requirements.txt pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ src/
COPY main.py ./

# Install the package in development mode
RUN pip install -e .

# Create volume mount point for database persistence
VOLUME ["/app/data"]

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash etymobot
USER etymobot

# Default command (can be overridden)
CMD ["python", "main.py", "--mode", "scheduled", "--db", "/app/data/etymobot.sqlite"] 