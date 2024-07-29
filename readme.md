# Ollama-Powered Streamlit App

This project integrates Ollama, an open-source large language model (LLM) server, with a Streamlit application for easy deployment and interaction.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Project Structure](#project-structure)
3. [Setup and Installation](#setup-and-installation)
4. [Running the Application](#running-the-application)
5. [Docker Deployment](#docker-deployment)
6. [Configuration](#configuration)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

* Docker
* Docker Compose (optional, for using docker-compose.yml)
* Bash-compatible shell (for running scripts)

## Project Structure

* `Dockerfile`: Defines the Docker image for the application.
* `docker-compose.yml`: Configures the Docker service for easy deployment.
* `docker-startup`: Bash script for building and deploying the Docker container.
* `entrypoint.sh`: Script that runs when the Docker container starts.
* `requirements.txt`: Lists Python dependencies for the project.
* `app.py`: the main app.
* `ollama_setup.py` : where the main communication with the model is described

## Setup and Installation

1. Clone this repository to your local machine.
2. Ensure Docker is installed and running on your system.
3. If you plan to use GPU acceleration, ensure you have the necessary GPU drivers and Docker GPU support installed.

## Running the Application

You can run the application using either Docker Compose or the provided `docker-startup` script.


### Using docker-startup Script (Recommended)

The `docker-startup` script provides three options:

1. Build the Docker image:
./docker-startup build

2. Deploy the application (CPU mode):
./docker-startup deploy

 - access the app at http://0.0.0.0:8501/

3. Deploy the application with GPU support:
./docker-startup deploy-gpu

  - access the app at http://0.0.0.0:8501/

### Using Docker Compose

1. Build and start the container:
docker-compose up --build
2. Access the Streamlit app at `http://localhost:8501`

## Docker Deployment

The application is containerized using Docker for easy deployment and consistency across different environments.

* The `Dockerfile` sets up the environment, installs dependencies, and configures the entry point.
* `entrypoint.sh` is executed when the container starts. It:
1. Starts the Ollama server
2. Pulls the specified LLM model (default is llama3)
3. Launches the Streamlit application

## Configuration

* **Ollama Model**: Change the default model by modifying the `OLLAMA_MODEL` environment variable in `docker-compose.yml`.
* **Ports**:
* Ollama server runs on port 11434
* Streamlit app runs on port 8501
* **Volume Mounting**: The application mounts `./data/ollama` to `/root/.ollama` in the container for persistent storage of Ollama data.

## Troubleshooting

* If you encounter issues with model downloads, check your internet connection and ensure you have enough disk space.
* For GPU deployment issues, verify that your system supports GPU passthrough to Docker containers.
* If the Streamlit app is not accessible, ensure that port 8501 is not being used by another application.

For any other issues or questions, please open an issue in the project repository.
