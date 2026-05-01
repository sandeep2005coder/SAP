; ─────────────────────────────────────────────────────────────
;  SAuP Agent Windows Installer
;  NSIS 3.x — Modern UI version
; ─────────────────────────────────────────────────────────────

; Include the Modern UI plugin that comes with NSIS
!include "MUI2.nsh"

; ── Basic info ───────────────────────────────────────────────
Name              "SAuP Agent"
OutFile           "SAuP-Agent-Setup-v1.0.exe"
InstallDir        "$PROGRAMFILES64\SAuP Agent"
RequestExecutionLevel admin

; ── MUI Settings ─────────────────────────────────────────────
!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"

; ── Pages ────────────────────────────────────────────────────
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; ── Language ─────────────────────────────────────────────────
!insertmacro MUI_LANGUAGE "English"

; ─────────────────────────────────────────────────────────────
;  INSTALL SECTION
; ─────────────────────────────────────────────────────────────
Section "SAuP Agent" SecMain

  SectionIn RO
  SetOutPath "$INSTDIR"

  ; Copy the agent exe built by PyInstaller
  File "dist\SAuP-Agent.exe"

  ; Write uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ; Add to Windows Add/Remove Programs
  WriteRegStr HKLM \
    "Software\Microsoft\Windows\CurrentVersion\Uninstall\SAuPAgent" \
    "DisplayName" "SAuP Agent"
  WriteRegStr HKLM \
    "Software\Microsoft\Windows\CurrentVersion\Uninstall\SAuPAgent" \
    "UninstallString" "$INSTDIR\Uninstall.exe"
  WriteRegStr HKLM \
    "Software\Microsoft\Windows\CurrentVersion\Uninstall\SAuPAgent" \
    "DisplayVersion" "1.0.0"
  WriteRegStr HKLM \
    "Software\Microsoft\Windows\CurrentVersion\Uninstall\SAuPAgent" \
    "Publisher" "SAuP Platform"

  ; Create Start Menu shortcut
  CreateDirectory "$SMPROGRAMS\SAuP Agent"
  CreateShortCut "$SMPROGRAMS\SAuP Agent\SAuP Agent.lnk" \
    "$INSTDIR\SAuP-Agent.exe"
  CreateShortCut "$SMPROGRAMS\SAuP Agent\Uninstall.lnk" \
    "$INSTDIR\Uninstall.exe"

  ; Create Desktop shortcut
  CreateShortCut "$DESKTOP\SAuP Agent.lnk" \
    "$INSTDIR\SAuP-Agent.exe"

  ; Auto-start on Windows boot
  WriteRegStr HKCU \
    "Software\Microsoft\Windows\CurrentVersion\Run" \
    "SAuPAgent" "$INSTDIR\SAuP-Agent.exe"

  ; Launch agent wizard immediately after install
  Exec "$INSTDIR\SAuP-Agent.exe"

SectionEnd

; ─────────────────────────────────────────────────────────────
;  UNINSTALL SECTION
; ─────────────────────────────────────────────────────────────
Section "Uninstall"

  Delete "$INSTDIR\SAuP-Agent.exe"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir  "$INSTDIR"

  Delete "$SMPROGRAMS\SAuP Agent\SAuP Agent.lnk"
  Delete "$SMPROGRAMS\SAuP Agent\Uninstall.lnk"
  RMDir  "$SMPROGRAMS\SAuP Agent"

  Delete "$DESKTOP\SAuP Agent.lnk"

  DeleteRegValue HKCU \
    "Software\Microsoft\Windows\CurrentVersion\Run" "SAuPAgent"

  DeleteRegKey HKLM \
    "Software\Microsoft\Windows\CurrentVersion\Uninstall\SAuPAgent"

SectionEnd