"""
audit_logger.py — Comprehensive audit logging system for Gold Tier AI Employee

Every action in the system is logged as JSON lines in silver_tier/Logs/YYYY-MM-DD.json.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict


LOG_DIR = Path(__file__).parent / "silver_tier" / "Logs"


class AuditLogger:
    """Writes structured audit log entries to daily JSON-line files."""

    ACTION_TYPES = {
        "email_send",
        "payment",
        "post",
        "watcher_trigger",
        "plan_created",
        "approval_request",
        "approval_granted",
        "approval_rejected",
        "error",
        "process_start",
        "process_stop",
        "briefing_generated",
        "invoice_created",
        "task_completed",
    }

    APPROVAL_STATUSES = {
        "approved",
        "pending",
        "rejected",
        "auto_approved",
        "not_required",
    }

    def __init__(self, log_dir: Path = None, actor: str = "claude_code"):
        self.log_dir = Path(log_dir) if log_dir else LOG_DIR
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.actor = actor

    def _log_file(self, date: datetime = None) -> Path:
        d = date or datetime.now()
        return self.log_dir / f"{d.strftime('%Y-%m-%d')}.json"

    def log_action(
        self,
        action_type: str,
        target: str,
        parameters: dict = None,
        approval_status: str = "not_required",
        approved_by: str = "n/a",
        result: str = "success",
        error_message: str = None,
    ) -> dict:
        """
        Write one audit entry to today's log file.

        Returns the log entry dict.
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "actor": self.actor,
            "target": target,
            "parameters": parameters or {},
            "approval_status": approval_status,
            "approved_by": approved_by,
            "result": result,
            "error_message": error_message,
        }

        log_file = self._log_file()
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            # Last-resort stderr logging so we never lose entries silently
            import sys
            print(f"[AuditLogger ERROR] Could not write to {log_file}: {e}", file=sys.stderr)

        return entry

    def get_logs(self, days: int = 7) -> list[dict]:
        """
        Return all log entries from the last `days` days, newest first.
        """
        entries = []
        today = datetime.now()
        for i in range(days):
            d = today - timedelta(days=i)
            log_file = self._log_file(d)
            if log_file.exists():
                try:
                    with open(log_file, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                try:
                                    entries.append(json.loads(line))
                                except json.JSONDecodeError:
                                    pass
                except Exception:
                    pass

        # Sort newest first
        entries.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
        return entries

    def generate_summary(self, days: int = 7) -> dict:
        """
        Summarise recent log entries by action_type and result.

        Returns a dict with:
          - period_days
          - total_actions
          - by_type: {action_type: count}
          - by_result: {result: count}
          - by_approval: {approval_status: count}
          - errors: list of error entries
          - first_seen / last_seen timestamps
        """
        entries = self.get_logs(days)

        by_type: dict[str, int] = defaultdict(int)
        by_result: dict[str, int] = defaultdict(int)
        by_approval: dict[str, int] = defaultdict(int)
        errors = []

        for e in entries:
            by_type[e.get("action_type", "unknown")] += 1
            by_result[e.get("result", "unknown")] += 1
            by_approval[e.get("approval_status", "unknown")] += 1
            if e.get("result") == "failure" or e.get("error_message"):
                errors.append(e)

        timestamps = [e.get("timestamp", "") for e in entries if e.get("timestamp")]

        return {
            "period_days": days,
            "total_actions": len(entries),
            "by_type": dict(by_type),
            "by_result": dict(by_result),
            "by_approval": dict(by_approval),
            "errors": errors,
            "first_seen": min(timestamps) if timestamps else None,
            "last_seen": max(timestamps) if timestamps else None,
        }


# ── Module-level convenience instance ────────────────────────────────────────
_default_logger = AuditLogger()


def log_action(action_type, target, parameters=None, approval_status="not_required",
               approved_by="n/a", result="success", error_message=None):
    """Module-level shortcut using the default AuditLogger instance."""
    return _default_logger.log_action(
        action_type=action_type,
        target=target,
        parameters=parameters,
        approval_status=approval_status,
        approved_by=approved_by,
        result=result,
        error_message=error_message,
    )


def get_logs(days: int = 7):
    return _default_logger.get_logs(days)


def generate_summary(days: int = 7):
    return _default_logger.generate_summary(days)


if __name__ == "__main__":
    import sys

    logger = AuditLogger()

    if "--summary" in sys.argv:
        summary = logger.generate_summary(days=7)
        print(json.dumps(summary, indent=2, default=str))
    elif "--test" in sys.argv:
        # Write a test entry
        entry = logger.log_action(
            action_type="email_send",
            target="test@example.com",
            parameters={"subject": "Test", "body_preview": "Hello"},
            approval_status="approved",
            approved_by="human",
            result="success",
        )
        print(f"Test entry written: {json.dumps(entry, indent=2)}")
    else:
        print("Usage: python audit_logger.py --test | --summary")
