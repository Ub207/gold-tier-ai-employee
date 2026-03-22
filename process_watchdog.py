#!/usr/bin/env python3
"""
watchdog.py — Process Health Monitor for AI Employee system

Monitors key background processes and auto-restarts them if they crash.
Writes status to silver_tier/Logs/watchdog.log.
Creates alert file in silver_tier/Needs_Action/ if a process fails to restart 3 times.

Usage:
    python watchdog.py                 # run watchdog loop (Ctrl+C to stop)
    python watchdog.py --check         # single status check and exit
    python watchdog.py --status        # print current process status
"""

import argparse
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
VAULT = BASE_DIR / "silver_tier"
LOG_DIR = VAULT / "Logs"
NEEDS_ACTION_DIR = VAULT / "Needs_Action"
WATCHDOG_LOG = LOG_DIR / "watchdog.log"

LOG_DIR.mkdir(parents=True, exist_ok=True)
NEEDS_ACTION_DIR.mkdir(parents=True, exist_ok=True)

CHECK_INTERVAL = 60        # seconds between checks
MAX_RESTART_ATTEMPTS = 3   # max before raising alert

PYTHON = sys.executable

MONITORED_PROCESSES = [
    {
        "name": "gmail_oauth_watcher",
        "script": "gmail_oauth_watcher.py",
        "restart_count": 0,
        "proc": None,
        "pid_file": BASE_DIR / "gmail_watcher.pid",
    },
    {
        "name": "whatsapp_watcher",
        "script": "whatsapp_watcher.py",
        "restart_count": 0,
        "proc": None,
        "pid_file": BASE_DIR / "whatsapp_watcher.pid",
    },
]

# ── Logging setup ─────────────────────────────────────────────────────────────

def _setup_logger() -> logging.Logger:
    logger = logging.getLogger("watchdog")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        # File handler
        fh = logging.FileHandler(WATCHDOG_LOG, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(fh)
        # Console handler
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter("%(asctime)s [WATCHDOG] %(message)s"))
        logger.addHandler(ch)
    return logger


logger = _setup_logger()


# ── Process management helpers ────────────────────────────────────────────────

def _read_pid_file(pid_file: Path) -> int | None:
    if pid_file.exists():
        try:
            return int(pid_file.read_text().strip())
        except Exception:
            pass
    return None


def _is_pid_running(pid: int) -> bool:
    """Check if a PID is alive (cross-platform)."""
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True, text=True
            )
            return str(pid) in result.stdout
        else:
            os.kill(pid, 0)  # signal 0 = just check
            return True
    except (ProcessLookupError, PermissionError, OSError):
        return False


def _is_script_running(script_name: str) -> bool:
    """Check if a Python script is running by name in process list."""
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["wmic", "process", "where", f"commandline like '%{script_name}%'", "get", "processid"],
                capture_output=True, text=True
            )
            lines = [l.strip() for l in result.stdout.splitlines() if l.strip() and l.strip().isdigit()]
            return len(lines) > 0
        else:
            result = subprocess.run(
                ["pgrep", "-f", script_name],
                capture_output=True, text=True
            )
            return bool(result.stdout.strip())
    except Exception:
        return False


def _check_process(p: dict) -> bool:
    """
    Returns True if process appears to be running.
    Checks: tracked subprocess -> pid file -> process name scan.
    """
    # 1) Check tracked subprocess handle
    proc = p.get("proc")
    if proc is not None and proc.poll() is None:
        return True

    # 2) Check pid file
    pid = _read_pid_file(p["pid_file"])
    if pid and _is_pid_running(pid):
        return True

    # 3) Fallback: scan process list by script name
    return _is_script_running(p["script"])


def _start_process(p: dict) -> subprocess.Popen | None:
    """Start the process, log stdout/stderr to logs/."""
    script = BASE_DIR / p["script"]
    if not script.exists():
        logger.warning(f"Script not found, skipping: {script}")
        return None

    log_path = BASE_DIR / "logs" / f"{p['name']}.log"
    log_path.parent.mkdir(exist_ok=True)

    try:
        kwargs = {}
        if sys.platform == "win32" and p["script"] == "whatsapp_watcher.py":
            # WhatsApp watcher needs its own console for Playwright
            kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
        else:
            with open(log_path, "a", encoding="utf-8") as lf:
                proc = subprocess.Popen(
                    [PYTHON, str(script)],
                    stdout=lf,
                    stderr=lf,
                    **kwargs,
                )
                p["proc"] = proc
                logger.info(f"Started {p['name']} (PID: {proc.pid})")
                return proc

        proc = subprocess.Popen([PYTHON, str(script)], **kwargs)
        p["proc"] = proc
        logger.info(f"Started {p['name']} (PID: {proc.pid})")
        return proc

    except Exception as e:
        logger.error(f"Failed to start {p['name']}: {e}")
        return None


def _create_alert(process_name: str, restart_count: int):
    """Write a Needs_Action alert file when a process can't be restarted."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    alert_file = NEEDS_ACTION_DIR / f"ALERT_system_down_{process_name}_{ts}.md"
    content = f"""# ALERT: Process Down — {process_name}
*Generated: {datetime.now().isoformat()}*

## Status
The process `{process_name}` has crashed and failed to restart after {restart_count} attempts.

## Action Required
1. Check the logs: `logs/{process_name}.log`
2. Check `silver_tier/Logs/watchdog.log` for restart history
3. Manually restart: `python {process_name.replace('_', '_')}.py`
4. If the script errors, investigate the root cause

## Auto-restart Failed
- Restart attempts: {restart_count}/{MAX_RESTART_ATTEMPTS}
- Time of last failure: {datetime.now().isoformat()}

---
*Generated by watchdog.py | Gold Tier*
"""
    alert_file.write_text(content, encoding="utf-8")
    logger.error(f"ALERT created: {alert_file.name}")


def _write_status(statuses: list[dict]):
    """Append a status summary line to watchdog.log."""
    status_line = " | ".join(
        f"{s['name']}: {'UP' if s['running'] else 'DOWN'}"
        for s in statuses
    )
    logger.info(f"Health check: {status_line}")


# ── Main watchdog loop ────────────────────────────────────────────────────────

def run_check(processes: list[dict]) -> list[dict]:
    """Run one health-check cycle. Returns status dicts."""
    statuses = []
    for p in processes:
        running = _check_process(p)
        statuses.append({"name": p["name"], "running": running})

        if not running:
            logger.warning(f"{p['name']} is DOWN")
            p["restart_count"] += 1

            if p["restart_count"] > MAX_RESTART_ATTEMPTS:
                logger.error(
                    f"{p['name']} exceeded max restart attempts ({MAX_RESTART_ATTEMPTS}). "
                    "Creating alert."
                )
                _create_alert(p["name"], p["restart_count"])
                # Reset so we don't spam alerts
                p["restart_count"] = 0
            else:
                logger.info(
                    f"Attempting restart #{p['restart_count']} for {p['name']}..."
                )
                proc = _start_process(p)
                if proc:
                    logger.info(f"{p['name']} restarted successfully (PID: {proc.pid})")
                else:
                    logger.error(f"Restart failed for {p['name']}")
        else:
            p["restart_count"] = 0  # Reset on success

    _write_status(statuses)
    return statuses


def print_status(processes: list[dict]):
    """Print current process status table to stdout."""
    print("\nWatchdog Status Report")
    print("=" * 50)
    print(f"{'Process':<30} {'Status':<10} {'Restarts'}")
    print("-" * 50)
    for p in processes:
        running = _check_process(p)
        status = "RUNNING" if running else "DOWN"
        print(f"{p['name']:<30} {status:<10} {p['restart_count']}")
    print("=" * 50)
    print(f"Check log: {WATCHDOG_LOG}\n")


def main():
    parser = argparse.ArgumentParser(description="AI Employee Process Watchdog")
    parser.add_argument("--check", action="store_true",
                        help="Single health check and exit")
    parser.add_argument("--status", action="store_true",
                        help="Print current process status and exit")
    args = parser.parse_args()

    processes = MONITORED_PROCESSES

    if args.status:
        print_status(processes)
        return

    if args.check:
        statuses = run_check(processes)
        all_up = all(s["running"] for s in statuses)
        sys.exit(0 if all_up else 1)

    # Continuous monitoring loop
    logger.info(f"Watchdog started. Monitoring {len(processes)} processes every {CHECK_INTERVAL}s.")
    logger.info(f"Processes: {', '.join(p['name'] for p in processes)}")

    try:
        while True:
            run_check(processes)
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        logger.info("Watchdog stopped by user.")


if __name__ == "__main__":
    main()
