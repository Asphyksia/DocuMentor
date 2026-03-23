FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mcp_wrapper.py .

EXPOSE 8000

CMD ["python", "mcp_wrapper.py"]
