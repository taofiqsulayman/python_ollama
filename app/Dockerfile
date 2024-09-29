# Base image for Python and dependencies
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
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
