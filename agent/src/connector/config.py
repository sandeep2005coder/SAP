# agent/src/connector/config.py
"""
Agent configuration. SAP credentials are stored ONLY in the local config file.
They are never sent to the SaaS control plane.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


CONFIG_PATH = Path.home() / ".saup" / "agent.json"
VERSION     = "1.0.0"
DEFAULT_LOCAL_BACKEND_URL = "http://localhost:3001"


@dataclass
class SapCredential:
    system_id:    str
    sap_system_id: str  # display alias
    ashost:       str   # SAP application server hostname
    sysnr:        str   # system number
    client:       str   # SAP client e.g. "100"
    user:         str   # read-only technical account
    password:     str   # stored locally only
    lang:         str = "EN"
    use_rfc:      bool = True


@dataclass
class AgentConfig:
    version:         str
    connector_id:    str
    tenant_id:       str
    saas_url:        str          # e.g. https://app.saup.io
    agent_secret:    str          # HMAC secret for API auth — never logged
    sap_credentials: list[SapCredential] = field(default_factory=list)
    poll_interval_s: int = 10     # seconds between job polls
    upload_threads:  int = 4
    work_dir:        str = str(Path.home() / ".saup" / "work")

    def __post_init__(self):
        self.saas_url = self.normalize_saas_url(self.saas_url)

    @staticmethod
    def normalize_saas_url(raw_url: str) -> str:
        url = (raw_url or "").strip().rstrip("/")
        if not url:
            return DEFAULT_LOCAL_BACKEND_URL

        if url.lower() in {"http://localhost:5173", "http://127.0.0.1:5173"}:
            return DEFAULT_LOCAL_BACKEND_URL

        return url

    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> "AgentConfig":
        if not path.exists():
            raise FileNotFoundError(
                f"Agent config not found at {path}. "
                "Run: python src/main.py --setup"
            )

        with open(path) as f:
            raw = json.load(f)

        creds = [SapCredential(**c) for c in raw.pop("sap_credentials", [])]

        return cls(
            version=VERSION,
            sap_credentials=creds,
            **{k: v for k, v in raw.items() if k != "sap_credentials"},
        )

    def get_credential(self, sap_system_id: str) -> Optional[SapCredential]:
        for cred in self.sap_credentials:
            if cred.sap_system_id == sap_system_id:
                return cred
        return None


EXAMPLE_CONFIG = {
    "connector_id":   "conn_REPLACE_WITH_YOUR_ID",
    "tenant_id":      "tenant_REPLACE",
    "saas_url":       "https://app.saup.io",
    "agent_secret":   "REPLACE_WITH_SHARED_SECRET_FROM_DASHBOARD",
    "poll_interval_s": 10,
    "upload_threads": 4,
    "sap_credentials": [
        {
            "system_id":      "PRD",
            "sap_system_id":  "PRD",
            "ashost":         "sap-prd.internal.corp.com",
            "sysnr":          "00",
            "client":         "100",
            "user":           "AUDIT_RO_SVC",
            "password":       "REPLACE_WITH_PASSWORD",
            "lang":           "EN",
            "use_rfc":        True
        }
    ]
}
