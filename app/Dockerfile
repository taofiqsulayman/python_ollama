FROM pytorch/pytorch:2.1.2-cuda12.1-cudnn8-devel

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3-dev \
    python3-pip \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    poppler-utils \
    antiword \
    git \
    wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install any additional system dependencies for document handling (optional)
RUN pip install --upgrade pip

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the Streamlit app code to the container
COPY . /app
WORKDIR /app

# Expose the port that Streamlit will run on
EXPOSE 8501

# Run Streamlit
CMD ["streamlit", "run", "main.py"]