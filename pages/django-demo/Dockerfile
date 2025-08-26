# Use Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /code

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    netcat-traditional \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /code/
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /code/

# Create necessary directories
RUN mkdir -p /code/static /code/media /code/logs

# Create a non-root user to run the application
RUN useradd -m -u 1000 django && \
    chown -R django:django /code

USER django

# Create entrypoint script
RUN echo '#!/bin/sh\n\
set -e\n\
\n\
echo "Waiting for PostgreSQL..."\n\
while ! nc -z ${POSTGRES_HOST:-postgres} ${POSTGRES_PORT:-5432}; do\n\
  sleep 0.1\n\
done\n\
echo "PostgreSQL started"\n\
\n\
echo "Waiting for MinIO..."\n\
while ! nc -z ${MINIO_HOST:-minio} ${MINIO_PORT:-9000}; do\n\
  sleep 0.1\n\
done\n\
echo "MinIO started"\n\
\n\
python manage.py migrate --noinput\n\
python manage.py collectstatic --noinput\n\
\n\
exec "$@"' > /code/entrypoint.sh && chmod +x /code/entrypoint.sh

# Run the entrypoint script
ENTRYPOINT ["/code/entrypoint.sh"]

# Default command
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]
