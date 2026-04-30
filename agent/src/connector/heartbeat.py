# agent/src/connector/heartbeat.py
"""
Sends periodic heartbeat to SaaS control plane.
Keeps connector status ONLINE and updates host metadata.
"""

import asyncio
import logging
import platform
import time

import aiohttp

from connector.config import AgentConfig

log = logging.getLogger("saup.heartbeat")

HEARTBEAT_INTERVAL = 30  # seconds


class HeartbeatService:
    def __init__(self, config: AgentConfig):
        self.config   = config
        self._running = True

    async def run(self):
        log.info("Heartbeat service started")
        async with aiohttp.ClientSession(headers=self._headers()) as session:
            while self._running:
                try:
                    await self._ping(session)
                except Exception as e:
                    log.warning(f"Heartbeat failed: {e}")
                await asyncio.sleep(HEARTBEAT_INTERVAL)

    async def stop(self):
        self._running = False

    async def _ping(self, session: aiohttp.ClientSession):
        url     = f"{self.config.saas_url}/api/v1/agent/heartbeat"
        payload = {
            "connectorId": self.config.connector_id,
            "version":     self.config.version,
            "hostInfo": {
                "hostname": platform.node(),
                "os":       f"{platform.system()} {platform.release()}",
                "arch":     platform.machine(),
            },
        }

        async with session.post(url, json=payload) as resp:
            if resp.status == 200:
                log.debug("Heartbeat OK")
            else:
                log.warning(f"Heartbeat returned {resp.status}")

    def _headers(self) -> dict:
        return {
            "X-Agent-Connector": self.config.connector_id,
            "X-Agent-Secret":    self.config.agent_secret,
            "Content-Type":      "application/json",
        }
