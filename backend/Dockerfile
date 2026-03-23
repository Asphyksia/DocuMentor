FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mcp_wrapper.py .
COPY bridge.py .

EXPOSE 8000 8001
