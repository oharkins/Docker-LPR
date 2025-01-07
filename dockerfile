# Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install required packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY stream_parser.py .

# These default values can be overridden using docker run arguments
CMD ["python", "stream_parser.py"]