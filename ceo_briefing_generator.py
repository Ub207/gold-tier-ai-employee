#!/usr/bin/env python3
"""
ceo_briefing_generator.py — Weekly Business Audit & CEO Briefing Generator

Reads vault data and generates a Monday morning briefing markdown file at
silver_tier/Briefings/YYYY-MM-DD_Monday_Briefing.md

Usage:
    python ceo_briefing_generator.py              # generate briefing now
    python ceo_briefing_generator.py --schedule   # register Windows Task Scheduler job
    python ceo_briefing_generator.py --stdout     # print briefing to stdout
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

VAULT = Path(__file__).parent / "silver_tier"
BRIEFINGS_DIR = VAULT / "Briefings"
DONE_DIR = VAULT / "Done"
LOGS_DIR = VAULT / "Logs"
PLANS_DIR = VAULT / "Plans"
IN_PROGRESS_DIR = VAULT / "In_Progress"
ACCOUNTING_DIR = VAULT / "Accounting"
BUSINESS_GOALS_FILE = VAULT / "Business_Goals.md"
ACCOUNTING_FILE = ACCOUNTING_DIR / "Current_Month.md"
BANK_TRANSACTIONS_FILE = ACCOUNTING_DIR / "Bank_Transactions.md"

# Import audit_logic for subscription analysis (graceful fallback if missing)
try:
    sys.path.insert(0, str(Path(__file__).parent))
    from audit_logic import load_transactions, audit_subscriptions, format_audit_report
    _AUDIT_AVAILABLE = True
except ImportError:
    _AUDIT_AVAILABLE = False


def _monday_of_week(dt: datetime) -> datetime:
    return dt - timedelta(days=dt.weekday())


def _read_file_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _read_audit_logs(days: int = 7) -> list[dict]:
    entries = []
    today = datetime.now()
    for i in range(days):
        d = today - timedelta(days=i)
        log_file = LOGS_DIR / f"{d.strftime('%Y-%m-%d')}.json"
        if log_file.exists():
            for line in log_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return entries


def _get_done_files_this_week() -> list[Path]:
    """Return Done/ files modified within the last 7 days."""
    if not DONE_DIR.exists():
        return []
    cutoff = datetime.now() - timedelta(days=7)
    result = []
    for f in DONE_DIR.glob("*.md"):
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime >= cutoff:
                result.append(f)
        except Exception:
            pass
    return sorted(result, key=lambda f: f.stat().st_mtime, reverse=True)


def _get_active_plans() -> list[Path]:
    """Return Plans/ files not yet completed."""
    if not PLANS_DIR.exists():
        return []
    done_names = {f.name for f in DONE_DIR.glob("*.md")} if DONE_DIR.exists() else set()
    plans = []
    for f in PLANS_DIR.glob("*.md"):
        if f.name not in done_names:
            plans.append(f)
    return sorted(plans, key=lambda f: f.stat().st_mtime, reverse=True)


def _get_bottleneck_plans(days_threshold: int = 3) -> list[Path]:
    """Return plans older than N days without completion."""
    cutoff = datetime.now() - timedelta(days=days_threshold)
    done_names = {f.name for f in DONE_DIR.glob("*.md")} if DONE_DIR.exists() else set()
    bottlenecks = []
    for f in PLANS_DIR.glob("*.md"):
        if f.name in done_names:
            continue
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                bottlenecks.append(f)
        except Exception:
            pass
    return sorted(bottlenecks, key=lambda f: f.stat().st_mtime)


def _parse_accounting_data(content: str) -> dict:
    """Extract financial data from Current_Month.md (simple markdown table parsing)."""
    data = {"this_week": "N/A", "month_to_date": "N/A", "progress_to_target": "N/A"}
    if not content:
        return data

    lines = content.splitlines()
    for line in lines:
        lower = line.lower()
        if "this week" in lower or "week total" in lower:
            # Extract number from line
            parts = line.split("|")
            for p in parts:
                p = p.strip()
                if any(c.isdigit() for c in p) and p != "This Week":
                    data["this_week"] = p
                    break
        elif "month to date" in lower or "mtd" in lower:
            parts = line.split("|")
            for p in parts:
                p = p.strip()
                if any(c.isdigit() for c in p):
                    data["month_to_date"] = p
                    break
        elif "progress" in lower or "target" in lower:
            parts = line.split("|")
            for p in parts:
                p = p.strip()
                if "%" in p:
                    data["progress_to_target"] = p
                    break

    return data


def _count_log_events(entries: list[dict]) -> dict:
    counts = {
        "total": len(entries),
        "email_send": 0,
        "post": 0,
        "approval_granted": 0,
        "error": 0,
        "watcher_trigger": 0,
    }
    for e in entries:
        at = e.get("action_type", "")
        if at in counts:
            counts[at] += 1
        if e.get("result") == "failure":
            counts["error"] += 1
    return counts


def _generate_proactive_suggestions(
    entries: list[dict],
    needs_action_files: list[Path],
    bottlenecks: list[Path],
) -> list[str]:
    suggestions = []

    if len(needs_action_files) > 5:
        suggestions.append(
            f"{len(needs_action_files)} items in Needs_Action — consider batch processing or delegation."
        )

    error_count = sum(1 for e in entries if e.get("result") == "failure")
    if error_count > 3:
        suggestions.append(
            f"{error_count} errors logged this week — review error logs and fix recurring issues."
        )

    if len(bottlenecks) > 2:
        suggestions.append(
            f"{len(bottlenecks)} plans stalled for 3+ days — schedule a review session."
        )

    post_count = sum(1 for e in entries if e.get("action_type") == "post")
    if post_count == 0:
        suggestions.append(
            "No social media posts logged this week — consider scheduling LinkedIn content."
        )

    email_count = sum(1 for e in entries if e.get("action_type") == "email_send")
    if email_count == 0:
        suggestions.append(
            "No outbound emails logged this week — check if email watcher is running."
        )

    if not suggestions:
        suggestions.append("System is running smoothly. No urgent actions identified.")

    return suggestions


def generate_briefing(output_stdout: bool = False) -> Path | None:
    """Generate the CEO briefing and save to Briefings/. Returns the file path."""
    now = datetime.now()
    monday = _monday_of_week(now)
    sunday = monday + timedelta(days=6)

    # Gather data
    business_goals = _read_file_safe(BUSINESS_GOALS_FILE)
    accounting_content = _read_file_safe(ACCOUNTING_FILE)
    audit_entries = _read_audit_logs(days=7)
    done_files = _get_done_files_this_week()
    active_plans = _get_active_plans()
    bottlenecks = _get_bottleneck_plans(days_threshold=3)
    accounting_data = _parse_accounting_data(accounting_content)
    log_counts = _count_log_events(audit_entries)

    needs_action_files = list(VAULT.glob("Needs_Action/*.md")) if (VAULT / "Needs_Action").exists() else []

    # Subscription & bank transaction audit (Gold Tier)
    subscription_section = ""
    if _AUDIT_AVAILABLE and BANK_TRANSACTIONS_FILE.exists():
        try:
            transactions = load_transactions(BANK_TRANSACTIONS_FILE)
            if transactions:
                audit_result = audit_subscriptions(transactions)
                subscription_section = format_audit_report(audit_result, period=f"Week of {monday.strftime('%b %d, %Y')}")
        except Exception as _audit_err:
            subscription_section = f"\n## Subscription Audit\n*Error running audit: {_audit_err}*\n"
    elif not _AUDIT_AVAILABLE:
        subscription_section = "\n## Subscription Audit\n*`audit_logic.py` not found — run `python audit_logic.py` to generate.*\n"
    else:
        subscription_section = "\n## Subscription Audit\n*`Bank_Transactions.md` not found — add transactions to `silver_tier/Accounting/Bank_Transactions.md`.*\n"

    suggestions = _generate_proactive_suggestions(audit_entries, needs_action_files, bottlenecks)

    # Add subscription flags to suggestions
    if _AUDIT_AVAILABLE and BANK_TRANSACTIONS_FILE.exists():
        try:
            transactions = load_transactions(BANK_TRANSACTIONS_FILE)
            if transactions:
                audit_result = audit_subscriptions(transactions)
                for flagged in audit_result.get("flagged", []):
                    if flagged.get("severity") in ("high", "medium"):
                        suggestions.insert(0, f"Subscription flag: **{flagged['name']}** — {flagged['reason']}")
        except Exception:
            pass

    # Compose completed tasks section
    if done_files:
        done_lines = []
        for f in done_files[:20]:
            # Try to extract first heading from file
            content = _read_file_safe(f)
            first_line = next(
                (l.lstrip("# ").strip() for l in content.splitlines() if l.strip()),
                f.stem
            )
            mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d")
            done_lines.append(f"- [{f.stem}] {first_line} *(completed ~{mtime})*")
        done_section = "\n".join(done_lines)
    else:
        done_section = "- No tasks completed this week (or Done/ folder is empty)"

    # Active plans section
    if active_plans:
        plan_lines = []
        for f in active_plans[:15]:
            age_days = (now - datetime.fromtimestamp(f.stat().st_mtime)).days
            plan_lines.append(f"- {f.stem} *(age: {age_days}d)*")
        plans_section = "\n".join(plan_lines)
    else:
        plans_section = "- No active plans"

    # Bottlenecks section
    if bottlenecks:
        bn_lines = []
        for f in bottlenecks[:10]:
            age_days = (now - datetime.fromtimestamp(f.stat().st_mtime)).days
            bn_lines.append(f"- **{f.stem}** — stalled for {age_days} days")
        bottleneck_section = "\n".join(bn_lines)
    else:
        bottleneck_section = "- No bottlenecks identified"

    # Executive summary
    completed_count = len(done_files)
    plan_count = len(active_plans)
    error_flag = " ⚠ Errors detected — review System Health section." if log_counts["error"] > 0 else ""
    exec_summary = (
        f"This week the system completed {completed_count} task(s) with "
        f"{plan_count} active plan(s) in progress. "
        f"{log_counts['total']} actions were logged across all subsystems.{error_flag}"
    )

    # Suggestions section
    suggestions_section = "\n".join(f"- {s}" for s in suggestions)

    briefing = f"""---
generated: {now.isoformat()}
period: {monday.strftime('%Y-%m-%d')} to {sunday.strftime('%Y-%m-%d')}
type: ceo_briefing
---

# Monday Morning CEO Briefing
*Generated: {now.strftime('%Y-%m-%d %H:%M')} | Period: {monday.strftime('%b %d')} – {sunday.strftime('%b %d, %Y')}*

## Executive Summary
{exec_summary}

## Revenue & Financial Overview
- **This Week**: {accounting_data['this_week']}
- **Month to Date**: {accounting_data['month_to_date']}
- **Progress to Target**: {accounting_data['progress_to_target']}

> *Update `silver_tier/Accounting/Current_Month.md` with latest figures for accurate tracking.*

## Completed Tasks This Week
{done_section}

## Active Plans
{plans_section}

## Bottlenecks
{bottleneck_section}

## System Health
- Actions logged this week: **{log_counts['total']}**
- Emails processed: **{log_counts['email_send']}**
- Social media posts: **{log_counts['post']}**
- Approvals granted: **{log_counts['approval_granted']}**
- Errors: **{log_counts['error']}**
- Watcher triggers: **{log_counts['watcher_trigger']}**

## Proactive Suggestions
{suggestions_section}
{subscription_section}
---
*Generated by Personal AI Employee | Gold Tier*
"""

    if output_stdout:
        print(briefing)
        return None

    BRIEFINGS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{now.strftime('%Y-%m-%d')}_Monday_Briefing.md"
    out_path = BRIEFINGS_DIR / filename
    out_path.write_text(briefing, encoding="utf-8")
    print(f"CEO Briefing generated: {out_path}")
    return out_path


def register_task_scheduler():
    """Register a Windows Task Scheduler job to run every Monday at 7 AM."""
    script_path = Path(__file__).resolve()
    python_exe = sys.executable

    task_xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-01-05T07:00:00</StartBoundary>
      <ScheduleByWeek>
        <WeeksInterval>1</WeeksInterval>
        <DaysOfWeek>
          <Monday />
        </DaysOfWeek>
      </ScheduleByWeek>
    </CalendarTrigger>
  </Triggers>
  <Actions Context="Author">
    <Exec>
      <Command>{python_exe}</Command>
      <Arguments>"{script_path}"</Arguments>
      <WorkingDirectory>{script_path.parent}</WorkingDirectory>
    </Exec>
  </Actions>
  <Settings>
    <ExecutionTimeLimit>PT30M</ExecutionTimeLimit>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
  </Settings>
</Task>"""

    xml_path = Path(__file__).parent / "_briefing_task.xml"
    xml_path.write_text(task_xml, encoding="utf-16")

    try:
        result = subprocess.run(
            ["schtasks", "/Create", "/TN", "AiEmployee_CEO_Briefing",
             "/XML", str(xml_path), "/F"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print("Task Scheduler job registered: AiEmployee_CEO_Briefing (Monday 7 AM)")
        else:
            print(f"Task Scheduler error: {result.stderr}")
    finally:
        xml_path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description="CEO Briefing Generator")
    parser.add_argument("--schedule", action="store_true",
                        help="Register Windows Task Scheduler job (Monday 7 AM)")
    parser.add_argument("--stdout", action="store_true",
                        help="Print briefing to stdout instead of saving")
    args = parser.parse_args()

    if args.schedule:
        register_task_scheduler()
    else:
        generate_briefing(output_stdout=args.stdout)


if __name__ == "__main__":
    import io as _io
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    main()
