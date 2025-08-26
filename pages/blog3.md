---
layout: post
title: "Building a Production-Ready Django Backend with PostgreSQL and MinIO"
date: 2025-01-03
---

# Building a Production-Ready Django Backend with PostgreSQL and MinIO

Ever wondered how to build a Django backend that can handle both structured data and file storage like a pro? Today, I'm going to walk you through setting up a Django application with PostgreSQL for your database needs and MinIO for object storage. This combo is battle-tested and scales beautifully.

## Why This Stack?

- **Django**: Batteries-included framework with excellent ORM and admin interface
- **PostgreSQL**: Rock-solid relational database with advanced features like JSONB fields
- **MinIO**: S3-compatible object storage that you can self-host or use in the cloud

## Project Structure

Let's start with a clean project structure:

```
django-backend/
├── docker-compose.yml
├── requirements.txt
├── .env
├── manage.py
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── __init__.py
│   ├── documents/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   └── urls.py
│   └── users/
│       ├── __init__.py
│       ├── models.py
│       ├── views.py
│       └── serializers.py
└── static/
```

## Setting Up Docker Compose

First, let's get our infrastructure running with Docker Compose. This makes development and deployment a breeze:

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: django_postgres
    environment:
      POSTGRES_DB: django_db
      POSTGRES_USER: django_user
      POSTGRES_PASSWORD: django_pass123
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    networks:
      - django_network

  minio:
    image: minio/minio:latest
    container_name: django_minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin123
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"
      - "9001:9001"
    networks:
      - django_network

  web:
    build: .
    container_name: django_web
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/code
    ports:
      - "8000:8000"
    environment:
      - DEBUG=True
      - DATABASE_URL=postgresql://django_user:django_pass123@postgres:5432/django_db
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=minioadmin
      - MINIO_SECRET_KEY=minioadmin123
    depends_on:
      - postgres
      - minio
    networks:
      - django_network

volumes:
  postgres_data:
  minio_data:

networks:
  django_network:
    driver: bridge
```

## Django Configuration

Now let's configure Django to use PostgreSQL and MinIO:

```python
# config/settings.py
import os
import dj_database_url
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dev-key-change-in-production')

DEBUG = os.environ.get('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'storages',
    'apps.documents',
    'apps.users',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

# Database Configuration
DATABASES = {
    'default': dj_database_url.config(
        default='postgresql://django_user:django_pass123@localhost:5432/django_db',
        conn_max_age=600
    )
}

# MinIO Configuration
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_ACCESS_KEY_ID = os.environ.get('MINIO_ACCESS_KEY', 'minioadmin')
AWS_SECRET_ACCESS_KEY = os.environ.get('MINIO_SECRET_KEY', 'minioadmin123')
AWS_STORAGE_BUCKET_NAME = 'django-media'
AWS_S3_ENDPOINT_URL = f"http://{os.environ.get('MINIO_ENDPOINT', 'localhost:9000')}"
AWS_S3_USE_SSL = False
AWS_S3_VERIFY = False
AWS_QUERYSTRING_AUTH = False
AWS_DEFAULT_ACL = None

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# CORS
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
```

## Dependencies

Here's what you'll need in your requirements.txt:

```txt
# requirements.txt
Django==4.2.7
djangorestframework==3.14.0
psycopg2-binary==2.9.9
dj-database-url==2.1.0
python-decouple==3.8
boto3==1.29.7
django-storages==1.14.2
django-cors-headers==4.3.0
Pillow==10.1.0
celery==5.3.4
redis==5.0.1
gunicorn==21.2.0
```

## Document Model with File Storage

Let's create a document model that stores metadata in PostgreSQL and files in MinIO:

```python
# apps/documents/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
import uuid

class DocumentCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Document Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Document(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        DocumentCategory, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='documents'
    )
    file = models.FileField(
        upload_to='documents/%Y/%m/%d/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'txt'])],
        help_text="Supported formats: PDF, DOC, DOCX, TXT"
    )
    thumbnail = models.ImageField(
        upload_to='thumbnails/%Y/%m/%d/',
        blank=True,
        null=True
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    metadata = models.JSONField(default=dict, blank=True)
    
    # Tracking fields
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    file_size = models.BigIntegerField(default=0)  # in bytes
    mime_type = models.CharField(max_length=100, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # Search and versioning
    version = models.IntegerField(default=1)
    search_vector = models.TextField(blank=True)  # For full-text search
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['uploaded_by', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
        super().save(*args, **kwargs)
```

## API Views and Serializers

Now let's create the API endpoints:

```python
# apps/documents/serializers.py
from rest_framework import serializers
from .models import Document, DocumentCategory

class DocumentCategorySerializer(serializers.ModelSerializer):
    document_count = serializers.IntegerField(source='documents.count', read_only=True)
    
    class Meta:
        model = DocumentCategory
        fields = ['id', 'name', 'description', 'document_count', 'created_at']

class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by_username = serializers.CharField(source='uploaded_by.username', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    file_url = serializers.SerializerMethodField()
    human_readable_size = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = [
            'id', 'title', 'description', 'category', 'category_name',
            'file', 'file_url', 'thumbnail', 'status', 'metadata',
            'uploaded_by', 'uploaded_by_username', 'file_size', 
            'human_readable_size', 'mime_type', 'created_at', 
            'updated_at', 'processed_at', 'version'
        ]
        read_only_fields = ['id', 'uploaded_by', 'file_size', 'mime_type', 'created_at', 'updated_at']
    
    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
        return None
    
    def get_human_readable_size(self, obj):
        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def create(self, validated_data):
        validated_data['uploaded_by'] = self.context['request'].user
        return super().create(validated_data)
```

```python
# apps/documents/views.py
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q
from django.utils import timezone
from .models import Document, DocumentCategory
from .serializers import DocumentSerializer, DocumentCategorySerializer

class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    parser_classes = (MultiPartParser, FormParser)
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'search_vector']
    ordering_fields = ['created_at', 'updated_at', 'title', 'file_size']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Filter by status if provided
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        
        # Filter by category if provided
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Filter by user's own documents if requested
        my_docs = self.request.query_params.get('my_documents')
        if my_docs and my_docs.lower() == 'true':
            queryset = queryset.filter(uploaded_by=user)
        
        return queryset.select_related('uploaded_by', 'category')
    
    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """Trigger document processing"""
        document = self.get_object()
        
        if document.status != 'draft':
            return Response(
                {'error': 'Document must be in draft status to process'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update status and trigger async processing
        document.status = 'processing'
        document.save()
        
        # Here you would trigger a Celery task for async processing
        # process_document.delay(document.id)
        
        return Response(
            {'message': 'Document processing started'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive a document"""
        document = self.get_object()
        document.status = 'archived'
        document.save()
        
        return Response(
            {'message': 'Document archived successfully'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get document statistics"""
        user = request.user
        
        stats = {
            'total_documents': Document.objects.count(),
            'my_documents': Document.objects.filter(uploaded_by=user).count(),
            'by_status': {},
            'by_category': {},
            'total_storage_used': 0
        }
        
        # Count by status
        for status_choice, status_display in Document.STATUS_CHOICES:
            count = Document.objects.filter(status=status_choice).count()
            stats['by_status'][status_display] = count
        
        # Count by category
        for category in DocumentCategory.objects.all():
            stats['by_category'][category.name] = category.documents.count()
        
        # Calculate total storage
        total_size = Document.objects.aggregate(
            total=models.Sum('file_size')
        )['total'] or 0
        
        # Convert to human-readable format
        stats['total_storage_used'] = self._format_bytes(total_size)
        
        return Response(stats)
    
    def _format_bytes(self, size):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"

class DocumentCategoryViewSet(viewsets.ModelViewSet):
    queryset = DocumentCategory.objects.all()
    serializer_class = DocumentCategorySerializer
    
    @action(detail=True, methods=['get'])
    def documents(self, request, pk=None):
        """Get all documents in a category"""
        category = self.get_object()
        documents = category.documents.all()
        serializer = DocumentSerializer(documents, many=True, context={'request': request})
        return Response(serializer.data)
```

## URL Configuration

Wire up the URLs for our API:

```python
# apps/documents/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DocumentViewSet, DocumentCategoryViewSet

router = DefaultRouter()
router.register(r'documents', DocumentViewSet)
router.register(r'categories', DocumentCategoryViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
```

```python
# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.documents.urls')),
    path('api/users/', include('apps.users.urls')),
    path('api-auth/', include('rest_framework.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
```

## MinIO Bucket Initialization

Create a management command to initialize MinIO buckets:

```python
# apps/documents/management/commands/init_minio.py
from django.core.management.base import BaseCommand
from django.conf import settings
import boto3
from botocore.exceptions import ClientError

class Command(BaseCommand):
    help = 'Initialize MinIO buckets for the application'
    
    def handle(self, *args, **options):
        # Create S3 client for MinIO
        s3_client = boto3.client(
            's3',
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            use_ssl=settings.AWS_S3_USE_SSL,
            verify=settings.AWS_S3_VERIFY
        )
        
        bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        
        try:
            # Check if bucket exists
            s3_client.head_bucket(Bucket=bucket_name)
            self.stdout.write(
                self.style.SUCCESS(f'Bucket "{bucket_name}" already exists')
            )
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # Create bucket
                try:
                    s3_client.create_bucket(Bucket=bucket_name)
                    self.stdout.write(
                        self.style.SUCCESS(f'Successfully created bucket "{bucket_name}"')
                    )
                    
                    # Set bucket policy for public read access (optional)
                    bucket_policy = {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Principal": {"AWS": "*"},
                                "Action": ["s3:GetObject"],
                                "Resource": f"arn:aws:s3:::{bucket_name}/*"
                            }
                        ]
                    }
                    
                    # Apply the policy
                    s3_client.put_bucket_policy(
                        Bucket=bucket_name,
                        Policy=json.dumps(bucket_policy)
                    )
                    
                    self.stdout.write(
                        self.style.SUCCESS('Bucket policy set for public read access')
                    )
                    
                except ClientError as create_error:
                    self.stdout.write(
                        self.style.ERROR(f'Failed to create bucket: {create_error}')
                    )
            else:
                self.stdout.write(
                    self.style.ERROR(f'Error checking bucket: {e}')
                )
```

## Testing the Setup

Here's a simple test to verify everything is working:

```python
# apps/documents/tests.py
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Document, DocumentCategory

class DocumentAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.category = DocumentCategory.objects.create(
            name='Reports',
            description='Monthly reports'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_create_document(self):
        """Test document creation with file upload"""
        # Create a test file
        test_file = SimpleUploadedFile(
            "test_document.txt",
            b"This is a test document content",
            content_type="text/plain"
        )
        
        data = {
            'title': 'Test Document',
            'description': 'A test document for unit testing',
            'category': self.category.id,
            'file': test_file,
            'metadata': '{"author": "Test User", "version": "1.0"}'
        }
        
        response = self.client.post('/api/documents/', data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Document.objects.count(), 1)
        
        document = Document.objects.first()
        self.assertEqual(document.title, 'Test Document')
        self.assertEqual(document.uploaded_by, self.user)
        self.assertTrue(document.file)
    
    def test_list_documents(self):
        """Test document listing and filtering"""
        # Create test documents
        Document.objects.create(
            title='Document 1',
            uploaded_by=self.user,
            category=self.category,
            status='completed'
        )
        Document.objects.create(
            title='Document 2',
            uploaded_by=self.user,
            status='draft'
        )
        
        # Test listing all documents
        response = self.client.get('/api/documents/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        
        # Test filtering by status
        response = self.client.get('/api/documents/?status=completed')
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'Document 1')
    
    def test_document_statistics(self):
        """Test document statistics endpoint"""
        Document.objects.create(
            title='Test Doc',
            uploaded_by=self.user,
            file_size=1024 * 1024  # 1MB
        )
        
        response = self.client.get('/api/documents/statistics/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_documents', response.data)
        self.assertIn('by_status', response.data)
        self.assertEqual(response.data['total_documents'], 1)
```

## Running the Application

To get everything up and running:

```bash
# Start the services
docker-compose up -d

# Wait for services to be ready
sleep 10

# Run migrations
docker-compose exec web python manage.py migrate

# Create a superuser
docker-compose exec web python manage.py createsuperuser

# Initialize MinIO buckets
docker-compose exec web python manage.py init_minio

# Run tests
docker-compose exec web python manage.py test

# Access the application
# Django Admin: http://localhost:8000/admin
# API: http://localhost:8000/api/
# MinIO Console: http://localhost:9001 (minioadmin/minioadmin123)
```

## Production Considerations

When deploying to production, remember to:

1. **Use environment variables** for all sensitive configuration
2. **Enable HTTPS** for both Django and MinIO
3. **Set up proper CORS policies** based on your frontend domains
4. **Implement rate limiting** using django-ratelimit or similar
5. **Add comprehensive logging** with structured output
6. **Set up monitoring** with tools like Sentry or DataDog
7. **Use a production WSGI server** like Gunicorn or uWSGI
8. **Configure PostgreSQL connection pooling** with pgbouncer
9. **Implement backup strategies** for both PostgreSQL and MinIO
10. **Add health check endpoints** for load balancers

## Performance Optimization Tips

```python
# Add this to your settings.py for better performance

# Connection pooling
DATABASES['default']['CONN_MAX_AGE'] = 600

# Caching with Redis
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Session storage in Redis
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Optimize database queries
DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
}
```

## Conclusion

There you have it! A complete Django backend with PostgreSQL for structured data and MinIO for object storage. This setup gives you the flexibility to handle complex data models while efficiently managing file uploads and storage. The best part? It's all containerized and ready to scale.

The combination of Django's robust ORM, PostgreSQL's reliability, and MinIO's S3-compatible API gives you a production-ready foundation that can grow with your application. Whether you're building a document management system, a media platform, or any application that needs both relational data and file storage, this stack has got you covered.

Happy coding, and remember: the best architecture is the one that solves your specific problems without overcomplicating things!