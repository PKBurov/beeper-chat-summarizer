FROM python:3.11-slim
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*
RUN pip install "websockets>=14.0" psycopg2-binary requests
COPY main.py .
CMD ["python", "-u", "main.py"]