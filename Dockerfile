FROM python:3.13-slim

# System packages required by:
# - librosa (ffmpeg, libsndfile)
# - python-magic (libmagic)
# - pillow (zlib, jpeg libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    libmagic1 \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first (better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Default command (CLI)
CMD ["python", "genius.py"]
