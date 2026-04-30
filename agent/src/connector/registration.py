# agent/src/connector/registration.py
"""
Registers (or re-registers) the connector with the SaaS on startup.
Updates host info and confirms active status.
"""

import logging
import platform

import aiohttp

from connector.config import AgentConfig

log = logging.getLogger("saup.registration")


async def register_connector(config: AgentConfig) -> None:
    url = f"{config.saas_url}/api/v1/agent/heartbeat"
    payload = {
        "connectorId": config.connector_id,
        "version":     config.version,
        "hostInfo": {
            "hostname": platform.node(),
            "os":       f"{platform.system()} {platform.release()}",
            "arch":     platform.machine(),
        },
    }

    headers = {
        "X-Agent-Connector": config.connector_id,
        "X-Agent-Secret":    config.agent_secret,
        "Content-Type":      "application/json",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status == 200:
                    log.info(f"Registered connector {config.connector_id} with control plane")
                else:
                    body = await resp.text()
                    log.error(f"Registration failed: HTTP {resp.status} — {body}")
                    raise RuntimeError(f"Connector registration failed: {resp.status}")
    except aiohttp.ClientConnectorError as e:
        log.error(f"Cannot reach SaaS at {config.saas_url}: {e}")
        log.warning("Starting in offline mode — will retry on next poll cycle")
