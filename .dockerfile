# Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install required packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY stream_parser.py .

# These default values can be overridden using docker run arguments
ENTRYPOINT ["python", "stream_parser.py"]
CMD ["--host", "166.142.83.208", "--port", "5002"]