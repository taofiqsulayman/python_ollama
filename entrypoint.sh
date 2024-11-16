#!/bin/bash
set -e

# Start Ollama server
echo "Starting Ollama server..."
ollama serve &

# Wait for Ollama server to start
echo "Waiting for Ollama server to start..."
sleep 5

# Pull required models
echo "Pulling Ollama models..."
ollama pull llama3.2:3b
ollama pull llama3.2-vision

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
while ! pg_isready -h db -p 5432 -U fileprocessor; do
    echo "PostgreSQL is unavailable - sleeping"
    sleep 1
done

# Start FastAPI server in background
echo "Starting FastAPI server..."
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 &

# Start Streamlit application in foreground
echo "Starting Streamlit application..."
streamlit run app.py --server.port=8501 --server.address=0.0.0.0

# Keep container running
wait -n