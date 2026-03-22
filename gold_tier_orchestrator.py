#!/usr/bin/env python3
"""
gold_tier_orchestrator.py — Master Gold Tier Orchestrator

Manages all AI Employee subsystems with full observability.

Features:
  - Starts all watchers (Gmail, WhatsApp)
  - Starts watchdog for process health monitoring
  - Runs workflow_runner on 5-minute schedule
  - Runs CEO briefing on Monday mornings (7 AM)
  - Logs all actions via AuditLogger
  - --status flag for system health dashboard
  - --test flag for dry-run mode

Usage:
    python gold_tier_orchestrator.py              # start full system
    python gold_tier_orchestrator.py --status     # show system health
    python gold_tier_orchestrator.py --test       # dry run (no real processes)
    python gold_tier_orchestrator.py --once       # run workflow once and exit
    python gold_tier_orchestrator.py --briefing   # generate CEO briefing now
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent
VAULT = BASE_DIR / "silver_tier"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

PYTHON = sys.executable

WORKFLOW_INTERVAL = 300      # 5 minutes
LINKEDIN_INTERVAL = 86400    # 24 hours
BRIEFING_INTERVAL = 86400    # 24 hours

# ── Logger setup ──────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("GoldTier")


# ── Import AuditLogger (graceful fallback) ────────────────────────────────────

try:
    from audit_logger import AuditLogger
    audit = AuditLogger()
except ImportError:
    class _NoOpAudit:
        def log_action(self, *a, **kw): pass
        def generate_summary(self, *a, **kw): return {}
    audit = _NoOpAudit()


# ── Process registry ──────────────────────────────────────────────────────────

class ProcessRegistry:
    """Tracks all running subprocesses and their metadata."""

    def __init__(self):
        self._procs: dict[str, dict] = {}

    def register(self, name: str, proc: subprocess.Popen | None):
        self._procs[name] = {
            "proc": proc,
            "pid": proc.pid if proc else None,
            "started_at": datetime.now().isoformat(),
            "restart_count": 0,
        }

    def get(self, name: str) -> subprocess.Popen | None:
        return self._procs.get(name, {}).get("proc")

    def is_alive(self, name: str) -> bool:
        proc = self.get(name)
        return proc is not None and proc.poll() is None

    def all_statuses(self) -> list[dict]:
        result = []
        for name, info in self._procs.items():
            proc = info.get("proc")
            alive = proc is not None and proc.poll() is None
            result.append({
                "name": name,
                "pid": info.get("pid"),
                "status": "RUNNING" if alive else "STOPPED",
                "started_at": info.get("started_at"),
                "restart_count": info.get("restart_count", 0),
            })
        return result

    def increment_restart(self, name: str):
        if name in self._procs:
            self._procs[name]["restart_count"] += 1


registry = ProcessRegistry()


# ── Process starters ──────────────────────────────────────────────────────────

def _log_proc(name: str) -> Path:
    return LOG_DIR / f"{name}.log"


def _popen(name: str, cmd: list[str], new_console: bool = False) -> subprocess.Popen | None:
    """Launch a subprocess, log output to logs/{name}.log."""
    if not Path(cmd[1]).exists() if len(cmd) > 1 else False:
        logger.warning(f"Script not found for {name}: {cmd[1]}")
        return None

    kwargs = {}
    if new_console and sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
    else:
        log_path = _log_proc(name)
        log_path.parent.mkdir(exist_ok=True)
        lf = open(log_path, "a", encoding="utf-8")
        kwargs["stdout"] = lf
        kwargs["stderr"] = lf

    try:
        proc = subprocess.Popen(cmd, **kwargs)
        logger.info(f"Started {name} (PID: {proc.pid})")
        return proc
    except Exception as e:
        logger.error(f"Failed to start {name}: {e}")
        audit.log_action("process_start", name, {"cmd": cmd},
                         result="failure", error_message=str(e))
        return None


def start_whatsapp_watcher() -> subprocess.Popen | None:
    proc = _popen("whatsapp_watcher", [PYTHON, str(BASE_DIR / "whatsapp_watcher.py")],
                  new_console=True)
    registry.register("whatsapp_watcher", proc)
    if proc:
        audit.log_action("process_start", "whatsapp_watcher", {"pid": proc.pid})
    return proc


def start_gmail_watcher() -> subprocess.Popen | None:
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        content = env_path.read_text(encoding="utf-8")
        has_creds = "EMAIL_ADDRESS=" in content and "EMAIL_APP_PASSWORD=" in content
    else:
        has_creds = bool(os.environ.get("EMAIL_ADDRESS"))

    if not has_creds:
        logger.info("Gmail Watcher skipped (credentials not set)")
        registry.register("gmail_watcher", None)
        return None

    proc = _popen("gmail_watcher", [PYTHON, str(BASE_DIR / "gmail_oauth_watcher.py")])
    registry.register("gmail_watcher", proc)
    if proc:
        audit.log_action("process_start", "gmail_watcher", {"pid": proc.pid})
    return proc


def start_watchdog() -> subprocess.Popen | None:
    proc = _popen("watchdog", [PYTHON, str(BASE_DIR / "process_watchdog.py")])
    registry.register("watchdog", proc)
    if proc:
        audit.log_action("process_start", "watchdog", {"pid": proc.pid})
    return proc


def start_auto_approver() -> subprocess.Popen | None:
    proc = _popen("auto_approver", [PYTHON, str(BASE_DIR / "auto_approver.py")])
    registry.register("auto_approver", proc)
    return proc


def start_approval_executor() -> subprocess.Popen | None:
    proc = _popen("approval_executor", [PYTHON, str(BASE_DIR / "approval_executor.py")])
    registry.register("approval_executor", proc)
    return proc


def start_filesystem_watcher() -> subprocess.Popen | None:
    proc = _popen("filesystem_watcher",
                  [PYTHON, str(BASE_DIR / "filesystem_watcher.py"), "--vault", "silver_tier"])
    registry.register("filesystem_watcher", proc)
    return proc


# ── One-shot runners ──────────────────────────────────────────────────────────

def run_workflow(dry_run: bool = False) -> bool:
    logger.info("Running workflow_runner.py ...")
    if dry_run:
        logger.info("[DRY RUN] workflow_runner.py skipped")
        return True

    log_path = _log_proc("workflow_runner")
    with open(log_path, "a", encoding="utf-8") as lf:
        lf.write(f"\n--- {datetime.now().isoformat()} ---\n")
        result = subprocess.run([PYTHON, str(BASE_DIR / "workflow_runner.py")],
                                stdout=lf, stderr=lf)
    success = result.returncode == 0
    audit.log_action(
        "watcher_trigger", "workflow_runner",
        {"returncode": result.returncode},
        result="success" if success else "failure",
    )
    return success


def run_linkedin_scheduler(type_key: str = "personal", dry_run: bool = False):
    logger.info(f"Running linkedin_scheduler.py --type {type_key} ...")
    if dry_run:
        logger.info(f"[DRY RUN] linkedin_scheduler.py --type {type_key} skipped")
        return

    log_path = _log_proc(f"linkedin_scheduler_{type_key}")
    with open(log_path, "a", encoding="utf-8") as lf:
        subprocess.run(
            [PYTHON, str(BASE_DIR / "linkedin_scheduler.py"), "--type", type_key],
            stdout=lf, stderr=lf,
        )


def run_ceo_briefing(dry_run: bool = False) -> Path | None:
    logger.info("Generating CEO Briefing ...")
    if dry_run:
        logger.info("[DRY RUN] CEO briefing skipped")
        return None

    try:
        from ceo_briefing_generator import generate_briefing
        out_path = generate_briefing()
        if out_path:
            audit.log_action("briefing_generated", str(out_path),
                             {"type": "monday_briefing"})
        return out_path
    except Exception as e:
        logger.error(f"CEO briefing generation failed: {e}")
        audit.log_action("briefing_generated", "CEO_Briefing",
                         result="failure", error_message=str(e))
        return None


# ── Health check / restart logic ──────────────────────────────────────────────

RESTARTABLE = {
    "whatsapp_watcher": start_whatsapp_watcher,
    "gmail_watcher": start_gmail_watcher,
    "watchdog": start_watchdog,
    "auto_approver": start_auto_approver,
    "approval_executor": start_approval_executor,
    "filesystem_watcher": start_filesystem_watcher,
}


def check_and_restart_processes():
    """Restart any registered process that has stopped."""
    for name, starter in RESTARTABLE.items():
        if not registry.is_alive(name):
            proc = registry.get(name)
            if proc is not None:  # was running but stopped
                logger.warning(f"{name} stopped unexpectedly — restarting...")
                registry.increment_restart(name)
                new_proc = starter()
                registry.register(name, new_proc)
                if new_proc:
                    audit.log_action("process_start", name,
                                     {"restart": True, "pid": new_proc.pid})


# ── Status dashboard ──────────────────────────────────────────────────────────

def print_status():
    """Print current system health dashboard."""
    print("\n" + "=" * 60)
    print("  GOLD TIER AI EMPLOYEE — SYSTEM STATUS")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Process status
    print("\nPROCESSES:")
    print(f"  {'Name':<30} {'Status':<12} {'PID':<10} {'Restarts'}")
    print("  " + "-" * 56)
    for s in registry.all_statuses():
        pid = str(s["pid"]) if s["pid"] else "N/A"
        print(f"  {s['name']:<30} {s['status']:<12} {pid:<10} {s['restart_count']}")

    # Vault stats
    print("\nVAULT:")
    for folder in ["Needs_Action", "Done", "Plans", "Approved", "Rejected",
                   "Pending_Approval", "In_Progress", "Briefings"]:
        d = VAULT / folder
        if d.exists():
            count = len(list(d.glob("*.md")))
            print(f"  {folder:<25} {count} files")

    # Audit log summary
    try:
        from audit_logger import AuditLogger
        summary = AuditLogger().generate_summary(days=7)
        print(f"\nAUDIT LOG (last 7 days):")
        print(f"  Total actions:  {summary.get('total_actions', 0)}")
        by_type = summary.get("by_type", {})
        for k, v in sorted(by_type.items(), key=lambda x: -x[1]):
            print(f"  {k:<25} {v}")
        errors = len(summary.get("errors", []))
        if errors:
            print(f"  ERRORS:         {errors} (check Logs/ folder)")
    except Exception as e:
        print(f"  (Audit log unavailable: {e})")

    print("\n" + "=" * 60 + "\n")


# ── Main orchestrator loop ────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Gold Tier Orchestrator")
    parser.add_argument("--status", action="store_true",
                        help="Print system health dashboard and exit")
    parser.add_argument("--test", action="store_true",
                        help="Dry run — start all monitoring but skip actual work")
    parser.add_argument("--once", action="store_true",
                        help="Run workflow once and exit")
    parser.add_argument("--briefing", action="store_true",
                        help="Generate CEO briefing now and exit")
    parser.add_argument("--no-watcher", action="store_true",
                        help="Skip WhatsApp/Gmail watchers")
    args = parser.parse_args()

    if args.status:
        print_status()
        return

    if args.briefing:
        run_ceo_briefing(dry_run=args.test)
        return

    if args.once:
        run_workflow(dry_run=args.test)
        return

    # Full startup
    logger.info("Gold Tier Orchestrator starting...")
    audit.log_action("process_start", "gold_tier_orchestrator",
                     {"mode": "test" if args.test else "production"})

    if not args.no_watcher and not args.test:
        start_whatsapp_watcher()
        start_gmail_watcher()
        start_filesystem_watcher()
        start_auto_approver()
        start_approval_executor()
        start_watchdog()
    elif args.test:
        logger.info("[DRY RUN] Skipping process startup")

    logger.info(f"Main loop started (interval: {WORKFLOW_INTERVAL}s)")
    last_linkedin_run = 0
    last_briefing_run = 0

    try:
        while True:
            if not args.test:
                check_and_restart_processes()

            run_workflow(dry_run=args.test)

            now = time.time()

            # LinkedIn — daily
            if now - last_linkedin_run >= LINKEDIN_INTERVAL:
                run_linkedin_scheduler("personal", dry_run=args.test)
                run_linkedin_scheduler("company", dry_run=args.test)
                last_linkedin_run = now

            # CEO Briefing — Monday mornings at 7 AM
            dt = datetime.now()
            if (dt.weekday() == 0 and dt.hour >= 7 and
                    now - last_briefing_run >= BRIEFING_INTERVAL):
                run_ceo_briefing(dry_run=args.test)
                last_briefing_run = now

            logger.info(f"Sleeping {WORKFLOW_INTERVAL}s ...")
            time.sleep(WORKFLOW_INTERVAL)

    except KeyboardInterrupt:
        logger.info("Gold Tier Orchestrator shutting down...")
        audit.log_action("process_stop", "gold_tier_orchestrator", {})
        for name in list(RESTARTABLE.keys()):
            proc = registry.get(name)
            if proc and proc.poll() is None:
                proc.terminate()
                logger.info(f"Stopped {name}")


if __name__ == "__main__":
    main()
