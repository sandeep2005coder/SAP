# agent/src/extractor/rfc_engine.py
"""
RFC/BAPI Extraction Engine — Primary extraction path.
Uses pyrfc (SAP NW RFC library) for direct function module calls.
No SAP GUI required. Stable, fast, enterprise-friendly.
"""

import hashlib
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import openpyxl
import csv

log = logging.getLogger("saup.rfc")

# pyrfc is optional — graceful fallback if not installed
try:
    import pyrfc
    PYRFC_AVAILABLE = True
except ImportError:
    PYRFC_AVAILABLE = False
    log.warning("pyrfc not available — RFC engine disabled. Install SAP NW RFC SDK + pyrfc.")


@dataclass
class ExtractionResult:
    files:        list[Path]
    record_count: int
    checksum:     str


# ── T-code to RFC Function Module Mapping ──────────────────────
# Maps SAP T-codes to their RFC-accessible equivalents
TCODE_FM_MAP: dict[str, dict] = {
    "FBL1N": {
        "fm":      "BAPI_VENDORDEBITBALANCE_GETDETAIL",
        "alt_fm":  "RFC_READ_TABLE",  # fallback
        "table":   "BSIK",            # open items
        "table2":  "BSAK",            # cleared items
    },
    "FBL5N": {
        "fm":    "RFC_READ_TABLE",
        "table": "BSID",              # customer open
        "table2": "BSAD",             # customer cleared
    },
    "MB51": {
        "fm":    "MB_DOCUMENT_LIST",
        "alt_fm": "RFC_READ_TABLE",
        "table": "MSEG",
    },
    "MB52": {
        "fm":    "RFC_READ_TABLE",
        "table": "MARD",              # storage location stock
    },
    "ME2M": {
        "fm":    "RFC_READ_TABLE",
        "table": "EKPO",              # PO line items
    },
}


class RfcEngine:
    def __init__(self):
        if not PYRFC_AVAILABLE:
            raise RuntimeError("pyrfc not installed. Cannot use RFC engine.")

    def execute(self, tcode: str, params: dict, credential, work_dir: Path) -> ExtractionResult:
        log.info(f"RFC extraction: {tcode} — params: {list(params.keys())}")

        conn_params = {
            "ashost": credential.ashost,
            "sysnr":  credential.sysnr,
            "client": credential.client,
            "user":   credential.user,
            "passwd": credential.password,
            "lang":   credential.lang,
        }

        with pyrfc.Connection(**conn_params) as conn:
            mapping = TCODE_FM_MAP.get(tcode)
            if not mapping:
                raise ValueError(f"No RFC mapping defined for T-code: {tcode}")

            records = self._call_fm(conn, tcode, mapping, params)
            log.info(f"Retrieved {len(records)} records for {tcode}")

        files    = self._write_output(records, tcode, params, work_dir)
        checksum = self._checksum_files(files)

        return ExtractionResult(
            files=files,
            record_count=len(records),
            checksum=checksum,
        )

    def _call_fm(self, conn, tcode: str, mapping: dict, params: dict) -> list[dict]:
        """Route to appropriate FM call based on tcode."""
        fm = mapping["fm"]

        if fm == "RFC_READ_TABLE":
            return self._read_table(conn, mapping["table"], params)

        if tcode == "MB51":
            return self._call_mb_document_list(conn, params)

        # Generic table read fallback
        return self._read_table(conn, mapping.get("table", ""), params)

    def _read_table(self, conn, table: str, params: dict) -> list[dict]:
        """Generic RFC_READ_TABLE call with WHERE clause construction."""
        where_clauses = self._build_where(params)

        result = conn.call("RFC_READ_TABLE", {
            "QUERY_TABLE": table,
            "DELIMITER":   "|",
            "OPTIONS":     [{"TEXT": w} for w in where_clauses],
            "ROWCOUNT":    0,  # 0 = no limit
        })

        fields  = [f["FIELDNAME"] for f in result["FIELDS"]]
        records = []

        for row in result["DATA"]:
            values = row["WA"].split("|")
            records.append(dict(zip(fields, values)))

        return records

    def _call_mb_document_list(self, conn, params: dict) -> list[dict]:
        """MB51 via BAPI MB_DOCUMENT_LIST."""
        result = conn.call("MB_DOCUMENT_LIST", {
            "PLANT":         params.get("plant", ""),
            "MATERIAL":      params.get("material", ""),
            "MOVE_TYPE":     params.get("movementType", ""),
            "PSTNG_DATE_FROM": params.get("dateFrom", ""),
            "PSTNG_DATE_TO":   params.get("dateTo", ""),
        })
        return result.get("MATERIAL_DOCUMENTS_OVERVIEW", [])

    def _build_where(self, params: dict) -> list[str]:
        clauses = []
        if params.get("dateFrom"):
            clauses.append(f"BUDAT >= '{params['dateFrom'].replace('-', '')}'")
        if params.get("dateTo"):
            clauses.append(f"BUDAT <= '{params['dateTo'].replace('-', '')}'")
        if params.get("companyCode"):
            clauses.append(f"BUKRS = '{params['companyCode']}'")
        if params.get("plant"):
            clauses.append(f"WERKS = '{params['plant']}'")
        return clauses

    def _write_output(self, records: list[dict], tcode: str, params: dict,
                      work_dir: Path) -> list[Path]:
        """Write records to XLSX, splitting at 1,000,000 rows (Excel limit)."""
        MAX_ROWS   = 1_000_000
        files      = []
        part       = 1

        for i in range(0, max(1, len(records)), MAX_ROWS):
            chunk    = records[i:i + MAX_ROWS]
            filename = f"{tcode}_{params.get('dateFrom', 'NA')}_to_{params.get('dateTo', 'NA')}_v{part}.xlsx"
            path     = work_dir / filename

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = tcode

            if chunk:
                ws.append(list(chunk[0].keys()))  # headers
                for row in chunk:
                    ws.append(list(row.values()))

            wb.save(path)
            files.append(path)
            part += 1

        return files

    def _checksum_files(self, files: list[Path]) -> str:
        h = hashlib.sha256()
        for f in sorted(files):
            h.update(f.name.encode())
            h.update(f.read_bytes())
        return h.hexdigest()
