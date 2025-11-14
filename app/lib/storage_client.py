"""Async AWS S3 client using aioboto3"""

import logging,tempfile,os
import tempfile
import os
from contextlib import asynccontextmanager
from typing import Optional
from pathlib import Path

import aioboto3
import aiohttp
from botocore.config import Config
from fastapi import UploadFile

# Import centralized settings
import sys
from pathlib import Path as PathLib

# Add project root to path to import settings
_project_root = PathLib(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from app.config.settings import settings

logger = logging.getLogger(__name__)


class AsyncS3Client:
    """Async AWS S3 client using aioboto3"""

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        region_name: Optional[str] = None,
        cdn_url: Optional[str] = None,
        retries: int = 5,
        timeout: int = 60,
    ):
        """
        Initialize async S3 client.

        Args:
            bucket_name: S3 bucket name (defaults to settings.S3_ASSET_BUCKET)
            region_name: AWS region (defaults to settings.AWS_REGION)
            cdn_url: CDN base URL (defaults to settings.CDN_URL)
            retries: Number of retry attempts
            timeout: Read timeout in seconds
        """
        self.bucket_name = bucket_name or settings.S3_ASSET_BUCKET
        self.region_name = region_name or settings.AWS_REGION
        self.cdn_url = cdn_url or settings.CDN_URL
        
        if not self.bucket_name:
            raise RuntimeError("Missing S3_ASSET_BUCKET in settings")
        if not self.region_name:
            raise RuntimeError("Missing AWS_REGION in settings")

        self.session = aioboto3.Session()
        self.endpoint_url = f"https://s3.{self.region_name}.amazonaws.com"

        self.config = Config(
            retries={"max_attempts": retries, "mode": "standard"},
            connect_timeout=5,
            read_timeout=timeout,
            s3={"addressing_style": "virtual"},
        )

    @asynccontextmanager
    async def get_client(self):
        """
        Context manager for S3 client.

        Usage:
            async with client.get_client() as s3:
                await s3.put_object(...)
        """
        async with self.session.client(
            "s3",
            region_name=self.region_name,
            endpoint_url=self.endpoint_url,
            config=self.config,
        ) as s3:
            yield s3

    async def upload_file(self, file: UploadFile, key: str) -> None:
        """Upload FastAPI UploadFile to S3."""
        try:
            contents = await file.read()
            await self.upload_bytes(
                file_bytes=contents,
                key=key,
                content_type=file.content_type or "application/octet-stream",
            )
            # Reset file pointer for potential reuse
            await file.seek(0)
        except Exception as e:
            logger.error(f"Failed to upload file to S3: {key} - {e}")
            raise

    async def upload_bytes(
        self,
        file_bytes: bytes,
        key: str,
        content_type: str = "application/octet-stream",
    ) -> None:
        """Upload raw bytes to S3."""
        try:
            async with self.get_client() as s3:
                await s3.put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=file_bytes,
                    ContentType=content_type,
                )
            logger.debug(f"Uploaded {len(file_bytes)} bytes to s3://{self.bucket_name}/{key}")
        except Exception as e:
            logger.error(f"Failed to upload bytes to S3: {key} - {e}")
            raise

    async def upload_from_url(self, url: str, key: str) -> None:
        """Download from URL and upload to S3."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as response:
                    response.raise_for_status()
                    content = await response.read()
                    content_type = response.headers.get("Content-Type", "application/octet-stream")

            await self.upload_bytes(file_bytes=content, key=key, content_type=content_type)
            logger.debug(f"Downloaded from {url} and uploaded to s3://{self.bucket_name}/{key}")
        except Exception as e:
            logger.error(f"Failed to upload from URL to S3: {url} -> {key} - {e}")
            raise

    async def delete(self, key: str) -> None:
        """Delete object from S3."""
        try:
            async with self.get_client() as s3:
                await s3.delete_object(Bucket=self.bucket_name, Key=key)
            logger.debug(f"Deleted s3://{self.bucket_name}/{key}")
        except Exception as e:
            logger.error(f"Failed to delete from S3: {key} - {e}")
            raise

    def get_public_url(self, key: str) -> str:
        """Get public CDN URL for object."""
        if self.cdn_url:
            # Ensure CDN URL doesn't end with / and key doesn't start with /
            cdn_base = self.cdn_url.rstrip("/")
            clean_key = key.lstrip("/")
            return f"{cdn_base}/{clean_key}"
        else:
            # Fallback to direct S3 URL when CDN is not configured
            clean_key = key.lstrip("/")
            return f"https://{self.bucket_name}.s3.{self.region_name}.amazonaws.com/{clean_key}"

    async def generate_presigned_url(
        self, key: str, expires_in: int = 604800
    ) -> str:
        """
        Generate presigned GET URL.

        Args:
            key: S3 object key
            expires_in: URL expiration in seconds (default: 7 days)

        Returns:
            Presigned URL or CDN URL if CDN_URL is configured
        """
        # If CDN is configured, return CDN URL instead
        if self.cdn_url:
            return self.get_public_url(key)

        try:
            async with self.get_client() as s3:
                url = await s3.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket_name, "Key": key},
                    ExpiresIn=expires_in,
                )
            logger.debug(f"Generated presigned URL for s3://{self.bucket_name}/{key}")
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {key} - {e}")
            raise

    async def create_presigned_put_url(
        self, key: str, content_type: str = "image/png", expiration: int = 604800
    ) -> str:
        """
        Generate presigned PUT URL for client-side upload.

        Args:
            key: S3 object key
            content_type: Content type for the upload
            expiration: URL expiration in seconds (default: 7 days)

        Returns:
            Presigned PUT URL
        """
        try:
            async with self.get_client() as s3:
                url = await s3.generate_presigned_url(
                    "put_object",
                    Params={
                        "Bucket": self.bucket_name,
                        "Key": key,
                        "ContentType": content_type,
                    },
                    ExpiresIn=expiration,
                )
            logger.debug(f"Generated presigned PUT URL for s3://{self.bucket_name}/{key}")
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned PUT URL: {key} - {e}")
            raise

    async def download_to_bytes(self, key: str) -> bytes:
        """Download S3 object to bytes."""
        try:
            async with self.get_client() as s3:
                response = await s3.get_object(Bucket=self.bucket_name, Key=key)
                async with response["Body"] as stream:
                    data = await stream.read()
            logger.debug(f"Downloaded {len(data)} bytes from s3://{self.bucket_name}/{key}")
            return data
        except Exception as e:
            logger.error(f"Failed to download from S3: {key} - {e}")
            raise

    async def download_to_temp(self, key: str, tmp_dir: Path) -> str:
        """Download S3 object to temporary file."""
        try:
            data = await self.download_to_bytes(key)
            ext = os.path.splitext(key)[1] or ""
            fd, tmp_path = tempfile.mkstemp(suffix=ext, dir=str(tmp_dir))
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            logger.debug(f"Downloaded s3://{self.bucket_name}/{key} to {tmp_path}")
            return tmp_path
        except Exception as e:
            logger.error(f"Failed to download to temp: {key} - {e}")
            raise

    async def list_objects(self, prefix: str) -> list[str]:
        """
        List objects in S3 bucket with given prefix.

        Args:
            prefix: S3 key prefix

        Returns:
            List of S3 keys
        """
        try:
            keys = []
            async with self.get_client() as s3:
                paginator = s3.get_paginator("list_objects_v2")
                async for page in paginator.paginate(
                    Bucket=self.bucket_name, Prefix=prefix
                ):
                    if "Contents" in page:
                        for obj in page["Contents"]:
                            keys.append(obj["Key"])
            logger.debug(f"Listed {len(keys)} objects with prefix: {prefix}")
            return keys
        except Exception as e:
            logger.error(f"Failed to list S3 objects: {prefix} - {e}")
            return []

