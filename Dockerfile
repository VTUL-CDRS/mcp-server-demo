FROM python:3.13-slim

WORKDIR /app

# Install dependencies first (layer-cached separately from data)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy data and server
COPY maps.jsonl .
COPY server.py .

EXPOSE 8000

CMD ["python3", "server.py", "--host", "0.0.0.0", "--port", "8000"]
