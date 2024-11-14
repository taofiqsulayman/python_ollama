
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

# Keycloak (Temporary Development Settings)
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=fileprocessor
KEYCLOAK_CLIENT_ID=file-processor-client
KEYCLOAK_CLIENT_SECRET=your-client-secret
KEYCLOAK_ADMIN_USERNAME=admin
KEYCLOAK_ADMIN_PASSWORD=admin

# Application Settings
DEBUG=True
SECRET_KEY=your-secret-key
MAX_FILE_SIZE=10485760
UPLOAD_FOLDER=./uploads
LOG_LEVEL=DEBUG

#HuggingFace Token
API_KEY=your-hugging-face-token

#AWS Bucket
BUCKET_NAME=your-bucket-name
```

## Step 4: Database Initialization
 Run the database initialization:
```bash
python init_db.py
```

## Step 5: Development Authentication Setup

For local development without Keycloak, you can use this simplified auth setup:

Check the file `dev_auth.py`


## Running the Application

1. Start the application:
```bash
streamlit run app.py
```

2. Access the application:
- Open your browser and go to `http://localhost:8501`
- Login using the development credentials:
  - Admin user: admin/admin123
  - Basic user: user/user123


# Keycloak Setup Guide

1. Run Keycloak in Docker:
```bash
docker run -p 8080:8080 -e KEYCLOAK_ADMIN=admin -e KEYCLOAK_ADMIN_PASSWORD=admin quay.io/keycloak/keycloak:latest start-dev
```

2. Access Keycloak Admin Console:
- Open: http://localhost:8080/admin/
- Login with admin/admin

3. Create a new realm:
- Click "Create Realm"
- Name it "fileprocessor"

4. Create a new client:
- Go to Clients → Create client
- Client ID: file-processor-client
- Client Protocol: openid-connect
- Access Type: confidential
- Valid Redirect URIs: http://localhost:8501/*

5. Get client secret:
- Go to Clients → file-processor-client → Credentials
- Copy the Secret value

6. Create roles:
- Go to Roles → Create role
- Create "basic" and "advanced" roles

7. Create users:
- Go to Users → Add user
- Create test users and assign roles

8. Update your .env file with the Keycloak settings

# AWS Bucket & HuggingFace Token Generation
AWS Bucket is used for the storage of extracted images and hugging face allows you to use the Llama model for image inferencing.

## 1. Configure AWS Credentials
Set up your AWS credentials to allow access to AWS services by using the AWS CLI. 

```bash
aws configure
```

This command will prompt you to enter your AWS Access Key, Secret Access Key, region, and output format. For more details, refer to [AWS CLI Configuration](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html).

### 2. Create an S3 Bucket
Create an S3 bucket to store the extracted images:

1. Go to your [AWS S3 Console](https://s3.console.aws.amazon.com/s3).
2. Click on **Create Bucket**.
3. Name your bucket and set the necessary permissions.

### 3. Set up a Hugging Face API Token
Generate a read token from your Hugging Face account to allow the project to access models:

1. Go to your [Hugging Face Account Settings](https://huggingface.co/settings/tokens).
2. Create a **Read Token** (API_KEY) and note it down for later use.