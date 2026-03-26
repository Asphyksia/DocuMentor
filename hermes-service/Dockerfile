FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy hermes-agent source
COPY hermes-agent/ ./hermes-agent/

# Copy service code
COPY hermes-service/server.py .

# Hermes config directory
RUN mkdir -p /root/.hermes

ENV HERMES_AGENT_DIR=/app/hermes-agent
ENV HERMES_PORT=8002
ENV PYTHONUNBUFFERED=1

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

CMD ["python", "server.py"]
