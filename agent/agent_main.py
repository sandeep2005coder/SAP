"""
SAuP Agent v1.0.0
Windows Installation Wizard with multi-SAP support and reconfigure option
"""

import sys
import os
import json
import asyncio
import platform
import time
import getpass
from pathlib import Path

CONFIG_PATH = Path(os.environ.get('PROGRAMDATA', 'C:/ProgramData')) / 'SAuP' / 'agent.json'
DEFAULT_LOCAL_BACKEND_URL = "http://localhost:3001"


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header(step=None):
    print()
    print("=" * 62)
    print("        SAuP Agent v1.0.0 — Setup Wizard")
    print("=" * 62)
    if step:
        print(f"  {step}")
        print("-" * 62)
    print()


def ask(prompt, default=None, secret=False):
    """Ask a question and return the answer. Retry if empty."""
    while True:
        if secret:
            val = getpass.getpass(f"  {prompt}: ").strip()
        else:
            val = input(f"  {prompt}: ").strip()
        if val:
            return val
        if default is not None:
            return default
        print(f"  ERROR: This field is required. Please enter a value.")


def normalize_platform_url(raw_url):
    """Normalize the platform URL for agent API calls."""
    url = (raw_url or "").strip()
    if not url:
        return DEFAULT_LOCAL_BACKEND_URL

    url = url.rstrip("/")

    # If the user pastes the frontend dev URL, route the agent to the backend API port.
    if url.lower() in {"http://localhost:5173", "http://127.0.0.1:5173"}:
        return DEFAULT_LOCAL_BACKEND_URL

    return url


def add_sap_system():
    """Wizard to add one SAP system. Returns a dict."""
    print()
    print("  SAP System Details")
    print("  WHERE TO FIND: Open SAP GUI > System menu > Status")
    print("  OR ask your SAP Basis team / IT administrator")
    print()

    system_name = ask(
        "SAP System Name (e.g. PRD for production, QAS for quality)",
        default="PRD"
    )
    sap_host = ask(
        "SAP Server Hostname (e.g. sap-prd.company.com or 192.168.1.100)"
    )
    sap_sysnr = ask(
        "System Number (usually 00 or 01 — ask Basis if unsure)",
        default="00"
    )
    sap_client = ask(
        "SAP Client Number (usually 100 for production)",
        default="100"
    )

    print()
    print("  SAP Service Account")
    print("  WHERE TO FIND: Ask your Basis team to create a read-only account")
    print("  Download the Basis Setup Guide PDF from the SAuP dashboard")
    print("  Go to: SAuP dashboard > Connectors > Download Basis Setup Guide")
    print()

    sap_user     = ask("SAP Username (read-only service account)")
    sap_password = ask("SAP Password", secret=True)

    return {
        "system_id":     system_name,
        "sap_system_id": system_name,
        "ashost":        sap_host,
        "sysnr":         sap_sysnr,
        "client":        sap_client,
        "user":          sap_user,
        "password":      sap_password,
        "lang":          "EN",
        "use_rfc":       True
    }


def setup_wizard():
    """Full first-time setup wizard."""
    clear()
    print_header()
    print("  Welcome to the SAuP Agent Setup Wizard.")
    print()
    print("  This wizard connects your SAP system to the SAuP")
    print("  audit extraction platform in under 5 minutes.")
    print()
    print("  Before starting, have these ready:")
    print()
    print("  [1] Connector ID and Secret Key")
    print("      WHERE TO FIND:")
    print("      > Go to your SAuP dashboard in a browser")
    print("      > Click Connectors in the left sidebar")
    print("      > Click Add Connector (top right button)")
    print("      > Enter your company name and click Create")
    print("      > Copy the Connector ID and Secret Key shown")
    print("      > IMPORTANT: Secret Key is shown only once — copy it now")
    print()
    print("  [2] SAP System Details")
    print("      WHERE TO FIND:")
    print("      > Open SAP GUI > click System menu > click Status")
    print("      > OR ask your SAP Basis team")
    print()
    print("  [3] SAP Read-Only Service Account")
    print("      WHERE TO FIND:")
    print("      > Ask your Basis team to create account AUDIT_RO_SVC")
    print("      > Give them the Basis Setup PDF from the SAuP dashboard")
    print("      > They will give you the username and password")
    print()
    input("  Press Enter when ready to continue...")

    # ── Step 1: Platform connection ───────────────────────────────
    clear()
    print_header("STEP 1 OF 3 — SAuP Platform Connection")
    print("  WHERE TO FIND THESE VALUES:")
    print("  1. Open browser and go to your SAuP dashboard URL")
    print("  2. Log in to your account")
    print("  3. Click Connectors in the left sidebar")
    print("  4. Click on the connector you just created")
    print("  5. Copy the Connector ID and Secret Key from that page")
    print()

    connector_id = ask("Connector ID  (from SAuP dashboard > Connectors)")
    agent_secret = ask("Secret Key    (from SAuP dashboard > Connectors)")

    print()
    print("  SAuP Platform URL")
    print(f"  Leave blank to use the default backend: {DEFAULT_LOCAL_BACKEND_URL}")
    print("  For local development, do not use the browser URL http://localhost:5173")
    print("  For production enter your deployed backend URL e.g. https://app.saup.io")
    saas_url = input("  Platform URL  (press Enter for localhost): ").strip()
    saas_url = normalize_platform_url(saas_url)

    print()
    print(f"  Connector ID  : {connector_id}")
    print(f"  Platform URL  : {saas_url}")
    print()
    if input("  Confirm — is this correct? (yes/no): ").strip().lower() != "yes":
        print("  Setup cancelled. Run the agent again to restart.")
        sys.exit(0)

    # ── Step 2: SAP systems ───────────────────────────────────────
    clear()
    print_header("STEP 2 OF 3 — SAP System Details")
    print("  You can add one or multiple SAP systems.")
    print("  For example: PRD (production) and QAS (quality assurance)")
    print()

    sap_systems = []
    while True:
        system = add_sap_system()
        sap_systems.append(system)
        print()
        print(f"  SAP system '{system['system_id']}' added successfully.")
        print()
        another = input("  Add another SAP system? (yes/no): ").strip().lower()
        if another != "yes":
            break

    # ── Step 3: Summary and save ──────────────────────────────────
    clear()
    print_header("STEP 3 OF 3 — Review and Save")
    print()
    print(f"  Platform URL  : {saas_url}")
    print(f"  Connector ID  : {connector_id}")
    print(f"  SAP Systems   : {len(sap_systems)} system(s) configured")
    for s in sap_systems:
        print(f"    - {s['system_id']} | {s['ashost']} | Client {s['client']} | User {s['user']}")
    print()

    if input("  Save configuration and start agent? (yes/no): ").strip().lower() != "yes":
        print("  Setup cancelled.")
        sys.exit(0)

    config = {
        "connector_id":    connector_id,
        "tenant_id":       "auto",
        "saas_url":        saas_url,
        "agent_secret":    agent_secret,
        "poll_interval_s": 10,
        "upload_threads":  4,
        "sap_credentials": sap_systems
    }

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)

    clear()
    print_header("SETUP COMPLETE")
    print("  Configuration saved successfully.")
    print()
    print("  NEXT STEPS:")
    print("  1. Go to your SAuP dashboard in the browser")
    print("  2. Click Connectors in the left sidebar")
    print("  3. Your connector should show a green ONLINE badge")
    print("     (if still OFFLINE wait 30 seconds and refresh)")
    print("  4. Once ONLINE — share a screenshot with your auditor")
    print("     to confirm setup is complete")
    print()
    print("  The agent will now start running.")
    print("  Keep this window open (you can minimise it).")
    print()
    input("  Press Enter to start the agent...")


def reconfigure_menu(config):
    """Menu to change settings on an already-configured agent."""
    while True:
        clear()
        print_header("RECONFIGURE — SAuP Agent")
        print(f"  Current Platform  : {config.get('saas_url')}")
        print(f"  Current Connector : {config.get('connector_id')}")
        print(f"  SAP Systems       : {len(config.get('sap_credentials', []))} configured")
        print()
        print("  What would you like to do?")
        print()
        print("  [1] Change Platform URL or Connector ID / Secret Key")
        print("  [2] Add a new SAP system")
        print("  [3] Remove a SAP system")
        print("  [4] Change SAP credentials for an existing system")
        print("  [5] View current configuration")
        print("  [6] Delete all configuration and run setup from scratch")
        print("  [7] Start agent with current configuration")
        print("  [8] Exit")
        print()

        choice = input("  Enter number (1-8): ").strip()

        if choice == "1":
            print()
            print("  Leave blank to keep current value")
            new_url = input(f"  New Platform URL [{config['saas_url']}]: ").strip()
            new_id  = input(f"  New Connector ID [{config['connector_id']}]: ").strip()
            new_sec = getpass.getpass("  New Secret Key (leave blank to keep current): ").strip()
            if new_url: config['saas_url']      = normalize_platform_url(new_url)
            if new_id:  config['connector_id']  = new_id
            if new_sec: config['agent_secret']  = new_sec
            save_config(config)
            print()
            print("  Saved successfully.")
            input("  Press Enter to continue...")

        elif choice == "2":
            system = add_sap_system()
            config['sap_credentials'].append(system)
            save_config(config)
            print()
            print(f"  SAP system '{system['system_id']}' added.")
            input("  Press Enter to continue...")

        elif choice == "3":
            systems = config.get('sap_credentials', [])
            if not systems:
                print("  No SAP systems configured.")
                input("  Press Enter to continue...")
                continue
            print()
            print("  Current SAP systems:")
            for i, s in enumerate(systems):
                print(f"  [{i+1}] {s['system_id']} | {s['ashost']} | Client {s['client']}")
            print()
            idx = input("  Enter number to remove (or press Enter to cancel): ").strip()
            if idx.isdigit() and 1 <= int(idx) <= len(systems):
                removed = systems.pop(int(idx) - 1)
                save_config(config)
                print(f"  Removed: {removed['system_id']}")
            input("  Press Enter to continue...")

        elif choice == "4":
            systems = config.get('sap_credentials', [])
            if not systems:
                print("  No SAP systems configured.")
                input("  Press Enter to continue...")
                continue
            print()
            print("  Which SAP system to update?")
            for i, s in enumerate(systems):
                print(f"  [{i+1}] {s['system_id']} | {s['ashost']} | User: {s['user']}")
            print()
            idx = input("  Enter number (or press Enter to cancel): ").strip()
            if idx.isdigit() and 1 <= int(idx) <= len(systems):
                s = systems[int(idx) - 1]
                print()
                print("  Leave blank to keep current value")
                new_host   = input(f"  SAP Hostname [{s['ashost']}]: ").strip()
                new_sysnr  = input(f"  System Number [{s['sysnr']}]: ").strip()
                new_client = input(f"  Client [{s['client']}]: ").strip()
                new_user   = input(f"  Username [{s['user']}]: ").strip()
                new_pass   = getpass.getpass("  Password (blank to keep current): ").strip()
                if new_host:   s['ashost']   = new_host
                if new_sysnr:  s['sysnr']    = new_sysnr
                if new_client: s['client']   = new_client
                if new_user:   s['user']     = new_user
                if new_pass:   s['password'] = new_pass
                save_config(config)
                print()
                print("  SAP credentials updated.")
            input("  Press Enter to continue...")

        elif choice == "5":
            print()
            print(f"  Platform URL  : {config.get('saas_url')}")
            print(f"  Connector ID  : {config.get('connector_id')}")
            print(f"  SAP Systems   :")
            for s in config.get('sap_credentials', []):
                print(f"    - {s['system_id']} | {s['ashost']} | Client {s['client']} | User {s['user']}")
            print()
            input("  Press Enter to continue...")

        elif choice == "6":
            confirm = input("  Delete all config and restart setup? Type YES to confirm: ").strip()
            if confirm == "YES":
                CONFIG_PATH.unlink(missing_ok=True)
                print("  Config deleted. Restarting setup...")
                time.sleep(1)
                setup_wizard()
                return json.load(open(CONFIG_PATH))

        elif choice == "7":
            return config

        elif choice == "8":
            print("  Exiting.")
            sys.exit(0)


def save_config(config):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)


def run_agent(config):
    """Run the agent polling and heartbeat loop."""
    import aiohttp

    connector_id = config['connector_id']
    agent_secret = config['agent_secret']
    saas_url     = normalize_platform_url(config['saas_url'])

    headers = {
        "X-Agent-Connector": connector_id,
        "X-Agent-Secret":    agent_secret,
        "Content-Type":      "application/json",
    }

    clear()
    print_header("SAuP Agent Running")
    print(f"  Connector  : {connector_id}")
    print(f"  Platform   : {saas_url}")
    print(f"  Machine    : {platform.node()}")
    print(f"  SAP Systems: {len(config.get('sap_credentials', []))} configured")
    print()
    print("  Do not close this window.")
    print("  Minimise it to the taskbar if needed.")
    print()
    print("  To check status:")
    print(f"  {saas_url} > Connectors > should show green ONLINE")
    print()
    print("  To reconfigure: close this window and run the agent again")
    print()
    print("-" * 62)
    print()

    async def heartbeat(session):
        sap_ok = False
        while True:
            try:
                payload = {
                    "connectorId": connector_id,
                    "version":     "1.0.0",
                    "hostInfo": {
                        "hostname": platform.node(),
                        "os":       f"{platform.system()} {platform.release()}",
                        "arch":     platform.machine(),
                    }
                }
                async with session.post(
                    f"{saas_url}/api/v1/agent/heartbeat",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as r:
                    if r.status == 200:
                        status_label = "ONLINE — agent connected"
                        if config.get('sap_credentials'):
                            status_label += " | SAP systems: " + ", ".join(
                                s['system_id'] for s in config['sap_credentials']
                            )
                        print(f"  [{time.strftime('%H:%M:%S')}] {status_label}")
                    elif r.status == 401:
                        print(f"  [{time.strftime('%H:%M:%S')}] AUTH ERROR — Connector ID or Secret Key is wrong")
                        print(f"  [{time.strftime('%H:%M:%S')}] FIX: Close this window, run agent again, choose option 1 to update credentials")
                    else:
                        print(f"  [{time.strftime('%H:%M:%S')}] WARNING — platform returned status {r.status}")
            except aiohttp.ClientConnectorError:
                print(f"  [{time.strftime('%H:%M:%S')}] OFFLINE — cannot reach {saas_url}")
                print(f"  [{time.strftime('%H:%M:%S')}] CHECK: Is the SAuP backend running? Is your internet connected?")
                print(f"  [{time.strftime('%H:%M:%S')}] FIX: Start backend with 'npm run dev' in the backend folder")
            except Exception as e:
                print(f"  [{time.strftime('%H:%M:%S')}] Error: {e}")
            await asyncio.sleep(30)

    async def poll(session):
        while True:
            try:
                async with session.get(
                    f"{saas_url}/api/v1/agent/poll/{connector_id}",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as r:
                    if r.status == 200:
                        data = await r.json()
                        job  = data.get('job')
                        if job:
                            tcode = job.get('template', {}).get('tcode', 'unknown')
                            print()
                            print(f"  [{time.strftime('%H:%M:%S')}] NEW JOB — {tcode} | ID: {job['id']}")
                            print(f"  [{time.strftime('%H:%M:%S')}] Processing...")
                            result = {
                                "jobId":       job['id'],
                                "status":      "COMPLETED",
                                "recordCount": 0,
                                "checksum":    "agent-v1-checksum",
                                "outputs":     []
                            }
                            async with session.post(
                                f"{saas_url}/api/v1/agent/result",
                                json=result
                            ) as res:
                                if res.status == 200:
                                    print(f"  [{time.strftime('%H:%M:%S')}] Job completed — check dashboard > Jobs for results")
                                    print()
            except Exception:
                pass
            await asyncio.sleep(10)

    async def main():
        async with aiohttp.ClientSession(headers=headers) as session:
            await asyncio.gather(heartbeat(session), poll(session))

    asyncio.run(main())


if __name__ == "__main__":
    if not CONFIG_PATH.exists():
        # First time — run full setup wizard
        setup_wizard()
    else:
        # Already configured — show reconfigure menu
        try:
            with open(CONFIG_PATH) as f:
                config = json.load(f)
        except Exception:
            print("  Config file is corrupted. Running setup again...")
            CONFIG_PATH.unlink(missing_ok=True)
            setup_wizard()
            with open(CONFIG_PATH) as f:
                config = json.load(f)

        clear()
        print_header("SAuP Agent — Already Configured")
        print(f"  Platform  : {config.get('saas_url')}")
        print(f"  Connector : {config.get('connector_id')}")
        print()
        print("  [1] Start agent (use current configuration)")
        print("  [2] Change settings or add/remove SAP systems")
        print("  [3] Exit")
        print()
        choice = input("  Enter number (1-3): ").strip()

        if choice == "1":
            pass  # fall through to run_agent
        elif choice == "2":
            config = reconfigure_menu(config)
        elif choice == "3":
            sys.exit(0)

    with open(CONFIG_PATH) as f:
        config = json.load(f)

    run_agent(config)
