# agent/src/executor/engine_selector.py
"""
Routes job execution to RFC (primary) or GUI (fallback) engine.
Enterprise rule: RFC first, GUI only when RFC cannot reproduce exact behavior.
"""

import logging
from pathlib import Path

from connector.config import AgentConfig
from extractor.rfc_engine import RfcEngine, ExtractionResult

log = logging.getLogger("saup.engine_selector")


class EngineSelector:
    def __init__(self, config: AgentConfig):
        self.config     = config
        self._rfc_engine = None
        self._gui_engine = None

    def execute(self, tcode: str, engine_type: str, params: dict,
                credential, work_dir: Path) -> ExtractionResult:

        if engine_type in ("RFC", "BAPI", "CUSTOM_FM"):
            return self._execute_rfc(tcode, params, credential, work_dir)

        if engine_type == "GUI_SCRIPT":
            return self._execute_gui(tcode, params, credential, work_dir)

        # Default: try RFC, fall back to GUI
        try:
            return self._execute_rfc(tcode, params, credential, work_dir)
        except Exception as e:
            log.warning(f"RFC failed for {tcode}: {e} — falling back to GUI")
            return self._execute_gui(tcode, params, credential, work_dir)

    def _execute_rfc(self, tcode: str, params: dict, credential, work_dir: Path) -> ExtractionResult:
        if not self._rfc_engine:
            self._rfc_engine = RfcEngine()
        return self._rfc_engine.execute(tcode, params, credential, work_dir)

    def _execute_gui(self, tcode: str, params: dict, credential, work_dir: Path) -> ExtractionResult:
        from extractor.gui_engine import GuiEngine
        if not self._gui_engine:
            self._gui_engine = GuiEngine()
            self._gui_engine.connect(credential)

        method_name = f"execute_{tcode.lower()}"
        method      = getattr(self._gui_engine, method_name, None)

        if not method:
            raise NotImplementedError(f"No GUI script for T-code: {tcode}")

        output_file = method(params, work_dir)
        checksum    = _sha256(output_file)

        return ExtractionResult(
            files=[output_file],
            record_count=_count_rows(output_file),
            checksum=checksum,
        )


def _sha256(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _count_rows(path: Path) -> int:
    try:
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True)
        ws = wb.active
        return ws.max_row - 1  # subtract header
    except Exception:
        return 0
