from __future__ import annotations

from typing import Optional

from datetime import timedelta
from io import BytesIO

import structlog
from minio import Minio

from backend.app.core.config import settings

logger = structlog.get_logger()

BUCKETS = ["papers", "blogs"]


class StorageService:
    def __init__(self):
        self._client: Optional[Minio] = None

    @property
    def client(self) -> Minio:
        if self._client is None:
            self._client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE,
            )
        return self._client

    def init_buckets(self):
        for bucket in BUCKETS:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
                logger.info("bucket_created", bucket=bucket)
            else:
                logger.info("bucket_exists", bucket=bucket)

    def upload_file(
        self, bucket: str, object_name: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        self.client.put_object(
            bucket,
            object_name,
            BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        logger.info("file_uploaded", bucket=bucket, key=object_name, size=len(data))
        return object_name

    def download_file(self, bucket: str, object_name: str) -> bytes:
        response = self.client.get_object(bucket, object_name)
        data = response.read()
        response.close()
        response.release_conn()
        return data

    def get_presigned_url(
        self, bucket: str, object_name: str, expires: int = 3600
    ) -> str:
        return self.client.presigned_get_object(
            bucket, object_name, expires=timedelta(seconds=expires)
        )

    def delete_file(self, bucket: str, object_name: str):
        self.client.remove_object(bucket, object_name)
        logger.info("file_deleted", bucket=bucket, key=object_name)


storage_service = StorageService()
