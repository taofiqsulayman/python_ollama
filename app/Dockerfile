# FROM pytorch/pytorch:2.1.2-cuda12.1-cudnn8-devel

# # Install system dependencies
# RUN apt-get update && apt-get install -y \
#     libgl1-mesa-glx \
#     libglib2.0-0 \
#     poppler-utils \
#     antiword \
#     git \
#     wget \
#     && apt-get clean \
#     && rm -rf /var/lib/apt/lists/*

# # Install any additional system dependencies for document handling (optional)
# RUN pip install --upgrade pip

# # Install Python dependencies
# COPY requirements.txt .
# RUN pip install -r requirements.txt

# # Copy the Streamlit app code to the container
# COPY . /app
# WORKDIR /app

# # Expose the port that Streamlit will run on
# EXPOSE 8501

# # Run Streamlit
# CMD ["streamlit", "run", "main.py"]


FROM pytorch/pytorch:2.1.2-cuda12.1-cudnn8-devel

WORKDIR /srv
RUN pip install vllm==0.3.3 --no-cache-dir

# if the model you want to serve requires you to accept the license terms,
# you must pass a HF_TOKEN environment variable, also ensure to pass a VLLM_API_KEY
# environment variable to authenticate your API
ENTRYPOINT ["python", "-m", "vllm.entrypoints.openai.api_server", \
            "--host", "0.0.0.0", "--port", "80", \
            "--model", "meta-llama/Llama-3.1-8B-Instruct", \
            # depending on your GPU, you might or might not need to pass --dtype
            "--dtype=half"]