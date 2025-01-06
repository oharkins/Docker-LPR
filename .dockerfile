# Use Python 3.9 slim image as base
FROM python:3.9-slim

# Set working directory in container
WORKDIR /app

# Copy the Python script
COPY stream_parser.py .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Create a non-root user for security
RUN useradd -m -r user && \
    chown -R user:user /app

# Switch to non-root user
USER user

# Command to run the script
# These default values can be overridden using docker run arguments
ENTRYPOINT ["python", "stream_parser.py"]
CMD ["--host", "166.142.83.208", "--port", "5002"]