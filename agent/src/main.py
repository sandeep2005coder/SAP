#!/usr/bin/env python3
"""
SAuP Client Agent
=================
Runs INSIDE the client network. Polls the SaaS control plane for jobs,
executes SAP extractions locally, and uploads results.

No inbound ports required. All communication is outbound TLS.
SAP credentials never leave this machine.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

from connector.config import AgentConfig
from connector.registration import register_connector
from connector.heartbeat import HeartbeatService
from connector.poller import JobPoller
from executor.engine_selector import EngineSelector
from uploader.upload_manager import UploadManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Path.home() / ".saup" / "agent.log"),
    ]
)
log = logging.getLogger("saup.agent")


async def main():
    config = AgentConfig.load()
    log.info(f"SAuP Agent v{config.version} starting — connector: {config.connector_id}")

    # Register / re-register with control plane
    await register_connector(config)

    # Services
    heartbeat = HeartbeatService(config)
    uploader  = UploadManager(config)
    engine    = EngineSelector(config)
    poller    = JobPoller(config, engine, uploader)

    # Graceful shutdown
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.ensure_future(shutdown(heartbeat, poller)))

    # Run heartbeat and polling concurrently
    await asyncio.gather(
        heartbeat.run(),
        poller.run(),
    )


async def shutdown(heartbeat, poller):
    log.info("Shutting down agent gracefully...")
    await heartbeat.stop()
    await poller.stop()
    asyncio.get_event_loop().stop()


if __name__ == "__main__":
    asyncio.run(main())
