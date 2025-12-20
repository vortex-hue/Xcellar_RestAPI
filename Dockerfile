FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        gcc \
        python3-dev \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Create entrypoint script
RUN chmod +x /app/scripts/entrypoint.sh

# Expose port (Render uses PORT env var, default to 8000)
EXPOSE 8000

# Run entrypoint (entrypoint.sh will use gunicorn if no command is provided)
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD []

