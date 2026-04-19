"""MinIO / S3-compatible object storage service for papers and blogs."""

from __future__ import annotations

import asyncio
import io
import logging
from typing import Any

from minio import Minio
from minio.error import S3Error

logger = logging.getLogger(__name__)

DEFAULT_BUCKETS = ("papers", "blogs")


class StorageService:
    """Wraps MinIO SDK for uploading, downloading, and managing research artefacts."""

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        *,
        secure: bool = True,
    ) -> None:
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )

    def init_buckets(self) -> None:
        for bucket in DEFAULT_BUCKETS:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
                logger.info("Created bucket: %s", bucket)

    async def upload_file(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        await asyncio.to_thread(
            self.client.put_object,
            bucket,
            key,
            io.BytesIO(data),
            len(data),
            content_type=content_type,
        )
        logger.info("Uploaded %s/%s (%d bytes)", bucket, key, len(data))
        return f"{bucket}/{key}"

    async def get_presigned_url(
        self, bucket: str, key: str, expires: int = 3600
    ) -> str:
        from datetime import timedelta

        url = await asyncio.to_thread(
            self.client.presigned_get_object,
            bucket,
            key,
            expires=timedelta(seconds=expires),
        )
        return url

    async def download_file(self, bucket: str, key: str) -> bytes:
        def _download() -> bytes:
            response = self.client.get_object(bucket, key)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()

        return await asyncio.to_thread(_download)

    async def delete_file(self, bucket: str, key: str) -> None:
        await asyncio.to_thread(self.client.remove_object, bucket, key)
        logger.info("Deleted %s/%s", bucket, key)

    async def list_objects(
        self, bucket: str, prefix: str = ""
    ) -> list[dict[str, Any]]:
        def _list() -> list[dict[str, Any]]:
            objects = self.client.list_objects(bucket, prefix=prefix, recursive=True)
            return [
                {
                    "key": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                }
                for obj in objects
            ]

        return await asyncio.to_thread(_list)
