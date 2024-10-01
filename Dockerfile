FROM ollama/ollama

WORKDIR /root

COPY requirements.txt ./

COPY entrypoint.sh ./

COPY app.py ./

COPY utils.py ./

COPY ollama_setup.py ./

COPY docker-startup ./

RUN apt update
RUN apt-get install -y python3 python3-pip git
RUN pip install -r requirements.txt

EXPOSE 8501
EXPOSE 11434
ENTRYPOINT ["./entrypoint.sh"]
