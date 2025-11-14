from app.lib.storage_client import AsyncS3Client
from typing import Optional
from loguru import logger as lg

s3_client = AsyncS3Client()


async def storage_create_signed_url(bucket: str, key: str, expires: int = 604800) -> Optional[str]:
    """Create signed URL for storage object"""
    try:
        url = await s3_client.generate_presigned_url(key=key, expires_in=expires)
        return url
    except Exception as e:
        lg.warning(f"Signed URL creation failed for {bucket}/{key}: {e}")
        return None

async def storage_upload_bytes(bucket: str, key: str, data: bytes, content_type: Optional[str] = None) -> Optional[str]:
    """Upload bytes to storage"""
    try:
        await s3_client.upload_bytes(
            file_bytes=data,
            key=key,
            content_type=content_type or "application/octet-stream"
        )
        # Return presigned URL or CDN URL
        return await storage_create_signed_url(bucket, key)
    except Exception as e:
        lg.error(f"Storage upload failed for {bucket}/{key}: {e}")
        return None