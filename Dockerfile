FROM python:3.12-slim

# Install system dependencies including FFmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for Hugging Face Spaces compatibility
RUN useradd -m -u 1000 user

WORKDIR /app

# Upgrade pip and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files and ensure user ownership
COPY --chown=user:user . .

# Ensure downloads directory exists with correct permissions
RUN mkdir -p /app/downloads && chown -R user:user /app

USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Expose HTTP port for Hugging Face (7860) and cloud platforms
EXPOSE 7860

# Run bots cluster (Film bot + Group bot + WebApp)
CMD ["python", "app.py"]


