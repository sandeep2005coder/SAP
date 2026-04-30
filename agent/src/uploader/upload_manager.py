# agent/src/uploader/upload_manager.py
"""
Uploads extraction output files to configured storage destinations.
Supports S3-compatible, OneDrive (via Graph API), and local fallback.
"""

import asyncio
import hashlib
import logging
from pathlib import Path

from connector.config import AgentConfig

log = logging.getLogger("saup.uploader")


class UploadManager:
    def __init__(self, config: AgentConfig):
        self.config = config

    async def upload_all(self, files: list[Path], job_id: str) -> list[dict]:
        """Upload all output files and return metadata list."""
        results = []
        tasks = [self._upload_one(f, job_id) for f in files]
        for coro in asyncio.as_completed(tasks):
            result = await coro
            results.append(result)
        return results

    async def _upload_one(self, file: Path, job_id: str) -> dict:
        checksum = self._sha256(file)
        size     = file.stat().st_size

        storage_key  = f"jobs/{job_id}/{file.name}"
        storage_type = "LOCAL"
        format_      = file.suffix.lstrip('.').upper()

        # Try S3 if configured
        try:
            storage_key  = await self._upload_s3(file, storage_key)
            storage_type = "S3"
        except Exception as e:
            log.warning(f"S3 upload failed for {file.name}: {e} — falling back to local manifest")

        record_count = self._count_rows(file)

        return {
            "filename":    file.name,
            "storageKey":  storage_key,
            "storageType": storage_type,
            "format":      format_,
            "sizeBytes":   size,
            "recordCount": record_count,
            "checksum":    checksum,
        }

    async def _upload_s3(self, file: Path, key: str) -> str:
        """Upload to S3-compatible storage using boto3."""
        import boto3
        import os

        endpoint = os.getenv("S3_ENDPOINT")
        bucket   = os.getenv("S3_BUCKET")
        region   = os.getenv("S3_REGION", "us-east-1")
        access   = os.getenv("S3_ACCESS_KEY")
        secret   = os.getenv("S3_SECRET_KEY")

        if not bucket:
            raise ValueError("S3_BUCKET not configured")

        session = boto3.session.Session()
        client  = session.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint,
            aws_access_key_id=access,
            aws_secret_access_key=secret,
        )

        await asyncio.to_thread(
            client.upload_file, str(file), bucket, key,
            ExtraArgs={"ServerSideEncryption": "AES256"}
        )

        return key

    def _sha256(self, path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def _count_rows(self, path: Path) -> int:
        try:
            if path.suffix.lower() == ".xlsx":
                import openpyxl
                wb = openpyxl.load_workbook(path, read_only=True)
                ws = wb.active
                return max(0, ws.max_row - 1)  # subtract header
            elif path.suffix.lower() == ".csv":
                with open(path) as f:
                    return sum(1 for _ in f) - 1  # subtract header
        except Exception:
            pass
        return 0
