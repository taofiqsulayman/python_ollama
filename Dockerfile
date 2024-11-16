# docker/app.Dockerfile
FROM ollama/ollama

WORKDIR /app

# Install system dependencies more efficiently
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    git \
    libgl1-mesa-glx \
    libglib2.0-0 \
    postgresql-client \
    antiword \
    && rm -rf /var/lib/apt/lists/* \
    && pip3 install --no-cache-dir pip --upgrade

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Expose ports for FastAPI and Streamlit
EXPOSE 8000 8501

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["./entrypoint.sh"]