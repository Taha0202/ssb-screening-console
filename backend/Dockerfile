FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AI_INFERENCE_MODE="LOCAL / OFFLINE" \
    OFFLINE_MODE=true

WORKDIR /app

# Install system dependencies for OpenCV and image forensics
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and sample data
COPY . .

# Ensure storage directories exist
RUN mkdir -p data/uploads data/heatmaps data/sample_documents

# Expose port
EXPOSE 8000

# Run database migration/initialization and launch server
CMD ["sh", "-c", "python -m app.db.init_db && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
