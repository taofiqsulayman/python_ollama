FROM ollama/ollama

# Install NVIDIA Container Toolkit dependencies
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

WORKDIR /app

# Install system dependencies including CUDA
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    git \
    libgl1-mesa-glx \
    libglib2.0-0 \
    postgresql-client \
    antiword \
    nvidia-cuda-toolkit \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Expose ports
EXPOSE 8000 8501

# Set environment variables
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    CUDA_VISIBLE_DEVICES=all

    
ENTRYPOINT ["./entrypoint.sh"]