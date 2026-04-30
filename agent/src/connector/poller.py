# agent/src/connector/poller.py
"""
Polls the SaaS control plane for new jobs.
Executes them locally and posts results back.
"""

import asyncio
import hashlib
import json
import logging
import time
from pathlib import Path

import aiohttp

from connector.config import AgentConfig
from executor.engine_selector import EngineSelector
from uploader.upload_manager import UploadManager

log = logging.getLogger("saup.poller")


class JobPoller:
    def __init__(self, config: AgentConfig, engine: EngineSelector, uploader: UploadManager):
        self.config   = config
        self.engine   = engine
        self.uploader = uploader
        self._running = True
        self._current_job = None

    async def run(self):
        log.info(f"Poller started — interval: {self.config.poll_interval_s}s")
        async with aiohttp.ClientSession(headers=self._headers()) as session:
            while self._running:
                try:
                    await self._poll_once(session)
                except Exception as e:
                    log.error(f"Poll error: {e}", exc_info=True)
                await asyncio.sleep(self.config.poll_interval_s)

    async def stop(self):
        self._running = False

    async def _poll_once(self, session: aiohttp.ClientSession):
        url = f"{self.config.saas_url}/api/v1/agent/poll/{self.config.connector_id}"
        async with session.get(url) as resp:
            if resp.status != 200:
                log.warning(f"Poll returned {resp.status}")
                return

            data = await resp.json()
            job  = data.get("job")
            if not job:
                return

        log.info(f"Received job {job['id']} — template: {job['template']['tcode']}")
        self._current_job = job["id"]

        try:
            await self._execute_job(session, job)
        except Exception as e:
            log.error(f"Job {job['id']} failed: {e}", exc_info=True)
            await self._post_result(session, job["id"], {
                "jobId":  job["id"],
                "status": "FAILED",
                "error":  str(e),
            })
        finally:
            self._current_job = None

    async def _execute_job(self, session: aiohttp.ClientSession, job: dict):
        job_id   = job["id"]
        template = job["template"]
        system   = job["sapSystem"]
        chunks   = job.get("chunks", [])

        cred = self.config.get_credential(system["name"])
        if not cred:
            raise ValueError(f"No credential configured for SAP system '{system['name']}'")

        work_dir = Path(self.config.work_dir) / job_id
        work_dir.mkdir(parents=True, exist_ok=True)

        if chunks:
            log.info(f"Job {job_id} has {len(chunks)} chunks")
            for chunk in chunks:
                await self._execute_chunk(session, job, chunk, cred, work_dir)
        else:
            # Single extraction
            await self._execute_single(session, job, cred, work_dir)

    async def _execute_single(self, session, job, cred, work_dir):
        job_id   = job["id"]
        template = job["template"]

        await self._log(session, job_id, "INFO", f"Starting RFC extraction for {template['tcode']}")

        result = await asyncio.to_thread(
            self.engine.execute,
            tcode       = template["tcode"],
            engine_type = template["engineType"],
            params      = job["params"],
            credential  = cred,
            work_dir    = work_dir,
        )

        outputs = await self.uploader.upload_all(result.files, job_id)

        await self._post_result(session, job_id, {
            "jobId":       job_id,
            "status":      "COMPLETED",
            "recordCount": result.record_count,
            "checksum":    result.checksum,
            "outputs":     outputs,
        })

        await self._log(session, job_id, "INFO",
                        f"Completed — {result.record_count} records, {len(result.files)} files")

    async def _execute_chunk(self, session, job, chunk, cred, work_dir):
        chunk_dir = work_dir / f"chunk_{chunk['chunkIndex']}"
        chunk_dir.mkdir(exist_ok=True)

        await self._log(session, job["id"], "INFO",
                        f"Chunk {chunk['chunkIndex']} ({chunk['chunkKey']}) starting")

        result = await asyncio.to_thread(
            self.engine.execute,
            tcode       = job["template"]["tcode"],
            engine_type = job["template"]["engineType"],
            params      = chunk["params"],
            credential  = cred,
            work_dir    = chunk_dir,
        )

        outputs = await self.uploader.upload_all(result.files, job["id"])

        await self._post_result(session, job["id"], {
            "jobId":       job["id"],
            "chunkId":     chunk["id"],
            "status":      "COMPLETED",
            "recordCount": result.record_count,
            "checksum":    result.checksum,
            "outputs":     outputs,
        })

    async def _post_result(self, session: aiohttp.ClientSession, job_id: str, payload: dict):
        url = f"{self.config.saas_url}/api/v1/agent/result"
        async with session.post(url, json=payload) as resp:
            if resp.status != 200:
                log.error(f"Failed to post result for {job_id}: {resp.status}")

    async def _log(self, session, job_id: str, level: str, message: str):
        url = f"{self.config.saas_url}/api/v1/agent/logs"
        payload = {
            "jobId": job_id,
            "lines": [{"level": level, "message": message, "timestamp": time.time() * 1000}]
        }
        async with session.post(url, json=payload) as resp:
            pass  # best-effort log shipping

    def _headers(self) -> dict:
        return {
            "X-Agent-Connector": self.config.connector_id,
            "X-Agent-Secret":    self.config.agent_secret,
            "Content-Type":      "application/json",
        }
