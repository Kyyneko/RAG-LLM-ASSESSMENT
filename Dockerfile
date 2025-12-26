# Base image with Python 3.11
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# Pre-download the embedding model during build
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# Copy application code
COPY . .

# Create directories for data
RUN mkdir -p data/vectorstore

# Expose port
EXPOSE 5002

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=main.py

# Run with gunicorn (sync workers instead of gevent)
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5002", "--timeout", "300", "--keep-alive", "300", "main:create_app()"]

