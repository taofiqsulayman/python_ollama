#!/bin/bash

# Start Ollama server
echo "Starting Ollama server..."
ollama serve &

# Wait for Ollama server to start
echo "Waiting for Ollama server to start..."
sleep 5

# Pull required models
echo "Pulling Ollama models..."
ollama pull llama3.2:3b
# ollama pull llama3.1

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
while ! pg_isready -h db -p 5432 -U fileprocessor; do
    sleep 1
done

# Wait for Keycloak to be ready
echo "Waiting for Keycloak..."
until curl --output /dev/null --silent --head --fail http://keycloak:8080; do
    sleep 1
done

# Initialize database
echo "Initializing database..."
python3 -c "from app.models import init_db; init_db()"

# Start Streamlit application
echo "Starting Streamlit application..."
streamlit run app/main.py --server.port=8501 --server.address=0.0.0.0