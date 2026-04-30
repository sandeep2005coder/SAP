# agent/src/extractor/gui_engine.py
"""
SAP GUI Scripting Engine — SECONDARY / FALLBACK path only.
Used when RFC/BAPI extraction cannot reproduce exact transaction behavior.

Requires:
- Windows OS
- SAP GUI 7.x installed with scripting enabled
- SAP GUI scripting settings: Options > Accessibility > Scripting = ON

Per SAP documentation, users MAY receive a notification popup when scripts
attach to SAP GUI sessions unless the notification setting is disabled by Basis.
Coordinate with client Basis team before enabling this engine in production.
"""

import logging
import time
from pathlib import Path

log = logging.getLogger("saup.gui")

# pywin32 / win32com only available on Windows
try:
    import win32com.client
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    log.warning("win32com not available (non-Windows OS). GUI engine disabled.")


class GuiEngine:
    def __init__(self):
        if not WIN32_AVAILABLE:
            raise RuntimeError("SAP GUI scripting requires Windows + pywin32.")
        self._session = None

    def connect(self, credential) -> None:
        """Connect to SAP GUI. SAP GUI must be running and logged in."""
        sap_gui    = win32com.client.GetObject("SAPGUI")
        app        = sap_gui.GetScriptingEngine
        connection = app.Children(0)
        self._session = connection.Children(0)
        log.info("Connected to SAP GUI session")

    def execute_fbl1n(self, params: dict, work_dir: Path) -> Path:
        s = self._session
        s.StartTransaction("FBL1N")

        self._fill(s, "RF05A-LIFNR", params.get("vendorCode", ""))
        self._fill(s, "RF05A-BUKRS", params.get("companyCode", ""))
        self._fill(s, "RF05A-AUGDT", params.get("dateFrom", ""))
        self._fill(s, "RF05A-AUGDT2", params.get("dateTo", ""))

        # Select item type
        item_status = params.get("itemStatus", "ALL")
        if item_status in ("ALL", "OPEN"):
            s.FindById("wnd[0]/usr/radRF05A-XOPVW").Select()
        if item_status == "CLEARED":
            s.FindById("wnd[0]/usr/radRF05A-XKLAR").Select()

        s.FindById("wnd[0]/tbar[1]/btn[8]").Press()  # Execute (F8)
        time.sleep(3)

        return self._export_to_local(s, work_dir, "FBL1N")

    def _fill(self, s, field_id: str, value: str):
        try:
            s.FindById(f"wnd[0]/usr/ctxt{field_id}").Text = value
        except Exception:
            pass  # field may not exist for all transactions

    def _export_to_local(self, s, work_dir: Path, tcode: str) -> Path:
        """Export ALV grid to local XLSX via SAP menu System > List > Save > Local File."""
        out_path = work_dir / f"{tcode}_gui_export.xlsx"

        try:
            # System > List > Save > Local File
            s.FindById("wnd[0]/mbar/menu[0]/menu[1]/menu[2]").Select()
            time.sleep(1)

            # Choose Spreadsheet
            s.FindById("wnd[1]/usr/subSUBSCREEN_STEPLOOP:SAPLSPO5:0150/sub:SAPLSPO5:0150/radSPOPLI-SELFLAG[1,0]").Select()
            s.FindById("wnd[1]/tbar[0]/btn[0]").Press()

            # Enter filename
            s.FindById("wnd[1]/usr/ctxtDY_FILENAME").Text = str(out_path)
            s.FindById("wnd[1]/tbar[0]/btn[11]").Press()
            time.sleep(2)
        except Exception as e:
            log.error(f"GUI export failed: {e}")
            raise

        return out_path

    def disconnect(self):
        self._session = None
