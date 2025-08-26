# minio_utils.py
"""
MinIO utility functions for advanced object storage operations.
This module provides helper functions for working with MinIO in Django.
"""

import io
import json
import hashlib
import mimetypes
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from PIL import Image
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.cache import cache


class MinIOClient:
    """
    A wrapper class for MinIO operations using boto3 S3 client.
    Provides high-level methods for common MinIO operations.
    """

    def __init__(self):
        """Initialize MinIO client with settings from Django configuration."""
        self.endpoint_url = settings.AWS_S3_ENDPOINT_URL
        self.access_key = settings.AWS_ACCESS_KEY_ID
        self.secret_key = settings.AWS_SECRET_ACCESS_KEY
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        self.use_ssl = getattr(settings, 'AWS_S3_USE_SSL', False)

        self.client = boto3.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            use_ssl=self.use_ssl,
            verify=False
        )

        self.resource = boto3.resource(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            use_ssl=self.use_ssl,
            verify=False
        )

    def ensure_bucket_exists(self, bucket_name: Optional[str] = None) -> bool:
        """
        Ensure that a bucket exists, create it if it doesn't.

        Args:
            bucket_name: Name of the bucket. Uses default if not provided.

        Returns:
            True if bucket exists or was created successfully.
        """
        bucket = bucket_name or self.bucket_name

        try:
            self.client.head_bucket(Bucket=bucket)
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                try:
                    self.client.create_bucket(Bucket=bucket)
                    return True
                except ClientError:
                    return False
            return False

    def upload_file_with_metadata(
        self,
        file_obj,
        object_name: str,
        metadata: Dict[str, str] = None,
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload a file to MinIO with custom metadata.

        Args:
            file_obj: File-like object to upload
            object_name: Name/path of the object in MinIO
            metadata: Custom metadata dictionary
            content_type: MIME type of the file

        Returns:
            Dictionary containing upload details
        """
        if metadata is None:
            metadata = {}

        # Add standard metadata
        metadata['upload-timestamp'] = datetime.utcnow().isoformat()
        metadata['original-name'] = getattr(file_obj, 'name', 'unknown')

        # Detect content type if not provided
        if not content_type:
            content_type, _ = mimetypes.guess_type(object_name)
            content_type = content_type or 'application/octet-stream'

        # Calculate file hash
        file_content = file_obj.read()
        file_hash = hashlib.sha256(file_content).hexdigest()
        metadata['sha256'] = file_hash

        # Reset file pointer
        file_obj.seek(0)

        try:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=object_name,
                Body=file_obj,
                ContentType=content_type,
                Metadata=metadata
            )

            return {
                'success': True,
                'object_name': object_name,
                'size': len(file_content),
                'hash': file_hash,
                'content_type': content_type,
                'url': self.get_object_url(object_name)
            }
        except ClientError as e:
            return {
                'success': False,
                'error': str(e),
                'object_name': object_name
            }

    def generate_thumbnail(
        self,
        image_key: str,
        thumbnail_size: Tuple[int, int] = (200, 200),
        thumbnail_prefix: str = 'thumbnails/'
    ) -> Optional[str]:
        """
        Generate a thumbnail for an image stored in MinIO.

        Args:
            image_key: Key of the original image in MinIO
            thumbnail_size: Tuple of (width, height) for thumbnail
            thumbnail_prefix: Prefix for thumbnail object names

        Returns:
            Key of the generated thumbnail or None if failed
        """
        try:
            # Download the original image
            response = self.client.get_object(
                Bucket=self.bucket_name,
                Key=image_key
            )
            image_data = response['Body'].read()

            # Open image with PIL
            image = Image.open(io.BytesIO(image_data))

            # Convert RGBA to RGB if necessary
            if image.mode in ('RGBA', 'LA', 'P'):
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                rgb_image.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = rgb_image

            # Generate thumbnail
            image.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)

            # Save thumbnail to bytes
            thumb_io = io.BytesIO()
            image.save(thumb_io, format='JPEG', quality=85, optimize=True)
            thumb_io.seek(0)

            # Generate thumbnail key
            thumbnail_key = f"{thumbnail_prefix}{image_key.replace('/', '_')}_thumb.jpg"

            # Upload thumbnail
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=thumbnail_key,
                Body=thumb_io,
                ContentType='image/jpeg',
                Metadata={
                    'original-image': image_key,
                    'thumbnail-size': f"{thumbnail_size[0]}x{thumbnail_size[1]}"
                }
            )

            return thumbnail_key

        except Exception as e:
            print(f"Error generating thumbnail: {e}")
            return None

    def get_presigned_url(
        self,
        object_name: str,
        expiration: int = 3600,
        method: str = 'GET'
    ) -> Optional[str]:
        """
        Generate a presigned URL for an object.

        Args:
            object_name: Name of the object in MinIO
            expiration: Time in seconds for the URL to remain valid
            method: HTTP method (GET or PUT)

        Returns:
            Presigned URL string or None if failed
        """
        cache_key = f"presigned_url:{self.bucket_name}:{object_name}:{method}"
        cached_url = cache.get(cache_key)

        if cached_url:
            return cached_url

        try:
            if method == 'GET':
                url = self.client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.bucket_name, 'Key': object_name},
                    ExpiresIn=expiration
                )
            elif method == 'PUT':
                url = self.client.generate_presigned_url(
                    'put_object',
                    Params={'Bucket': self.bucket_name, 'Key': object_name},
                    ExpiresIn=expiration
                )
            else:
                return None

            # Cache the URL for slightly less than its expiration time
            cache_timeout = max(expiration - 60, 60)
            cache.set(cache_key, url, cache_timeout)

            return url

        except ClientError:
            return None

    def list_objects_with_metadata(
        self,
        prefix: str = '',
        max_keys: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        List objects in a bucket with their metadata.

        Args:
            prefix: Prefix to filter objects
            max_keys: Maximum number of objects to return

        Returns:
            List of dictionaries containing object information
        """
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )

            objects = []
            for obj in response.get('Contents', []):
                # Get object metadata
                metadata_response = self.client.head_object(
                    Bucket=self.bucket_name,
                    Key=obj['Key']
                )

                objects.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'etag': obj['ETag'].strip('"'),
                    'content_type': metadata_response.get('ContentType', 'unknown'),
                    'metadata': metadata_response.get('Metadata', {})
                })

            return objects

        except ClientError:
            return []

    def copy_object(
        self,
        source_key: str,
        destination_key: str,
        destination_bucket: Optional[str] = None
    ) -> bool:
        """
        Copy an object within MinIO.

        Args:
            source_key: Key of the source object
            destination_key: Key for the destination object
            destination_bucket: Destination bucket (uses default if None)

        Returns:
            True if successful, False otherwise
        """
        dest_bucket = destination_bucket or self.bucket_name

        try:
            copy_source = {'Bucket': self.bucket_name, 'Key': source_key}
            self.client.copy_object(
                Bucket=dest_bucket,
                Key=destination_key,
                CopySource=copy_source
            )
            return True
        except ClientError:
            return False

    def delete_objects(self, object_keys: List[str]) -> Dict[str, Any]:
        """
        Delete multiple objects from MinIO.

        Args:
            object_keys: List of object keys to delete

        Returns:
            Dictionary with deletion results
        """
        if not object_keys:
            return {'deleted': [], 'errors': []}

        delete_objects = [{'Key': key} for key in object_keys]

        try:
            response = self.client.delete_objects(
                Bucket=self.bucket_name,
                Delete={'Objects': delete_objects}
            )

            return {
                'deleted': [obj['Key'] for obj in response.get('Deleted', [])],
                'errors': [
                    {'key': err['Key'], 'error': err['Message']}
                    for err in response.get('Errors', [])
                ]
            }
        except ClientError as e:
            return {
                'deleted': [],
                'errors': [{'error': str(e)}]
            }

    def get_object_url(self, object_name: str) -> str:
        """
        Get the public URL for an object.

        Args:
            object_name: Name of the object

        Returns:
            Public URL string
        """
        parsed_url = urlparse(self.endpoint_url)
        protocol = 'https' if self.use_ssl else 'http'
        return f"{protocol}://{parsed_url.netloc}/{self.bucket_name}/{object_name}"

    def set_bucket_lifecycle(
        self,
        days_to_expire: int = 90,
        prefix: str = 'temp/'
    ) -> bool:
        """
        Set lifecycle policy for automatic object expiration.

        Args:
            days_to_expire: Number of days before objects expire
            prefix: Prefix for objects to apply the policy to

        Returns:
            True if successful
        """
        lifecycle_policy = {
            'Rules': [
                {
                    'ID': 'auto-delete-rule',
                    'Status': 'Enabled',
                    'Filter': {'Prefix': prefix},
                    'Expiration': {'Days': days_to_expire}
                }
            ]
        }

        try:
            self.client.put_bucket_lifecycle_configuration(
                Bucket=self.bucket_name,
                LifecycleConfiguration=lifecycle_policy
            )
            return True
        except ClientError:
            return False

    def get_bucket_size(self) -> Dict[str, Any]:
        """
        Calculate the total size of all objects in a bucket.

        Returns:
            Dictionary with size information
        """
        total_size = 0
        total_count = 0

        try:
            paginator = self.client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name)

            for page in pages:
                for obj in page.get('Contents', []):
                    total_size += obj['Size']
                    total_count += 1

            return {
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'total_size_gb': round(total_size / (1024 * 1024 * 1024), 2),
                'object_count': total_count
            }
        except ClientError:
            return {
                'total_size_bytes': 0,
                'total_size_mb': 0,
                'total_size_gb': 0,
                'object_count': 0
            }

    def create_multipart_upload(
        self,
        object_name: str,
        content_type: str = 'application/octet-stream'
    ) -> Optional[str]:
        """
        Initiate a multipart upload for large files.

        Args:
            object_name: Name of the object to upload
            content_type: MIME type of the file

        Returns:
            Upload ID or None if failed
        """
        try:
            response = self.client.create_multipart_upload(
                Bucket=self.bucket_name,
                Key=object_name,
                ContentType=content_type
            )
            return response['UploadId']
        except ClientError:
            return None


# Singleton instance
minio_client = MinIOClient()


def sync_file_to_minio(local_path: str, object_name: str) -> bool:
    """
    Synchronize a local file to MinIO.

    Args:
        local_path: Path to the local file
        object_name: Name for the object in MinIO

    Returns:
        True if successful
    """
    try:
        with open(local_path, 'rb') as file_obj:
            result = minio_client.upload_file_with_metadata(
                file_obj,
                object_name,
                metadata={'source': 'local_sync'}
            )
            return result['success']
    except Exception:
        return False


def generate_signed_upload_url(
    object_name: str,
    content_type: str = 'application/octet-stream',
    expiration: int = 3600
) -> Optional[Dict[str, Any]]:
    """
    Generate a presigned URL for direct browser upload.

    Args:
        object_name: Name for the object
        content_type: MIME type of the file
        expiration: URL expiration time in seconds

    Returns:
        Dictionary with upload URL and fields
    """
    try:
        # Generate presigned POST URL
        response = minio_client.client.generate_presigned_post(
            Bucket=minio_client.bucket_name,
            Key=object_name,
            ExpiresIn=expiration
        )

        return {
            'url': response['url'],
            'fields': response['fields'],
            'object_name': object_name,
            'expires_in': expiration
        }
    except ClientError:
        return None
