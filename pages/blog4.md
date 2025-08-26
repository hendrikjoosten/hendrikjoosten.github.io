---
layout: post
title: "Quick and Dirty: Django + PostgreSQL + MinIO in 5 Minutes"
date: 2025-01-04
---

# Quick and Dirty: Django + PostgreSQL + MinIO in 5 Minutes

Look, sometimes you just need to get a Django backend running with proper database and file storage without all the fluff. Here's the absolute minimum you need.

## The Stack in One Docker Compose

```yaml
# docker-compose.yml
version: '3.8'
services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_PASSWORD: postgres
    volumes:
      - ./data/db:/var/lib/postgresql/data
  
  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - ./data/minio:/data
  
  web:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/code
    ports:
      - "8000:8000"
    depends_on:
      - db
      - minio
```

## Minimal Django Settings

```python
# settings.py
import os
import dj_database_url

# Database
DATABASES = {
    'default': dj_database_url.config(
        default='postgresql://postgres:postgres@db:5432/postgres'
    )
}

# MinIO for file storage
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_ACCESS_KEY_ID = 'minioadmin'
AWS_SECRET_ACCESS_KEY = 'minioadmin'
AWS_STORAGE_BUCKET_NAME = 'media'
AWS_S3_ENDPOINT_URL = 'http://minio:9000'
AWS_S3_USE_SSL = False
AWS_QUERYSTRING_AUTH = False
```

## Dead Simple File Upload Model

```python
# models.py
from django.db import models

class Document(models.Model):
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title
```

## Quick API View

```python
# views.py
from rest_framework import viewsets
from rest_framework.parsers import MultiPartParser
from .models import Document
from .serializers import DocumentSerializer

class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    parser_classes = (MultiPartParser,)
```

## The Serializer

```python
# serializers.py
from rest_framework import serializers
from .models import Document

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = '__all__'
```

## Requirements

```txt
Django==4.2.7
djangorestframework==3.14.0
psycopg2-binary==2.9.9
dj-database-url==2.1.0
boto3==1.29.7
django-storages==1.14.2
```

## Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /code
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
```

## Fire It Up

```bash
# Start everything
docker-compose up -d

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# You're done!
```

## What You Get

- PostgreSQL at `localhost:5432`
- MinIO at `localhost:9000` (console at `localhost:9001`)
- Django at `localhost:8000`
- File uploads stored in MinIO
- Database records in PostgreSQL

## Testing It Out

```bash
# Upload a file via curl
curl -X POST http://localhost:8000/api/documents/ \
  -H "Content-Type: multipart/form-data" \
  -F "title=My Document" \
  -F "file=@/path/to/file.pdf"

# List all documents
curl http://localhost:8000/api/documents/
```

## That's It

No fancy features, no complex configurations, just the bare minimum to get you started. Database for your data, MinIO for your files, Django to tie it together. 

Sometimes that's all you need.

Want more? Check out my [previous post](./blog3.md) for the full production setup with all the bells and whistles.