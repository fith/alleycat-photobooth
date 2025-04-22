FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    i2c-tools \
    gcc \
    build-essential \
    linux-headers-generic \
    ffmpeg

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ .

# Run the application
CMD ["python", "app.py"]
