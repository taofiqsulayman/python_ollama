#!/bin/bash

# Start the Ollama server at port 11434
echo "Starting the Ollama Server"
ollama serve &

echo "Waiting for models to downloads"
sleep 5 # Necessary if server is not yet up
ollama pull llama3.2:3b
ollama pull llama3.1

# Start the streamlit server, blocking exit
echo "Starting the Streamlit server"
streamlit run app.py --server.port=8501 --server.address=0.0.0.0