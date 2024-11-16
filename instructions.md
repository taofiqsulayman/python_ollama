
# Local Development Setup Guide

## Prerequisites

1. Python 3.8+ installed
2. Docker installed
3. pip or poetry for Python package management

## Step 1: Environment Setup

1. Create a new virtual environment:
```bash
# Using venv
python -m venv venv

# Activate the virtual environment
# On Windows
venv\Scripts\activate
# On Unix or MacOS
source venv/bin/activate
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

## Step 2: PostgreSQL Setup with Docker

1. Create a Docker container for PostgreSQL:
```bash
docker run --name fileprocessor-db \
  -e POSTGRES_DB=fileprocessor \
  -e POSTGRES_USER=fileprocessor \
  -e POSTGRES_PASSWORD=yourpassword \
  -p 5432:5432 \
  -d postgres:14
```

2. Verify the container is running:
```bash
docker ps
```

## Step 3: Environment Variables

Create a `.env` file in your project root:
```env
# Database
DATABASE_URL=postgresql://fileprocessor:yourpassword@localhost:5432/fileprocessor