FROM pytorch/pytorch:2.1.2-cuda12.1-cudnn8-devel

# Set the environment variable to avoid tzdata prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && \
    apt-get install -y \
    python3-pip \
    python3-dev \
    build-essential \
    curl \
    software-properties-common \
    antiword \
    poppler-utils \
    libgl1-mesa-glx \
    libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Copy requirements.txt first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Streamlit app code to the container
COPY . /app
WORKDIR /app

# Expose the port that Streamlit will run on
EXPOSE 8501

# Run Streamlit
CMD ["streamlit", "run", "main.py"]
