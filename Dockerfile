# Use official lightweight Python image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies (including potential PDF parsing or image libraries)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . .

# Create persistent directories for SQLite DB, Inbox files, and Processed logs
RUN mkdir -p data inbox processed

# Expose backend port
EXPOSE 8000

# Start command running Uvicorn server (host 0.0.0.0 is critical for Docker)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
