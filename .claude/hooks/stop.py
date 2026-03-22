#!/usr/bin/env python3
"""
Ralph Wiggum Stop Hook
Intercepts Claude's exit attempt and re-injects the prompt if task not done.

Claude Code calls this hook before stopping. If unfinished work remains in
Needs_Action/, we tell Claude to keep working.
"""

import sys
import json
import os
from pathlib import Path


def main():
    # Read hook input from stdin
    try:
        raw = sys.stdin.read()
        hook_input = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, Exception):
        hook_input = {}

    stop_reason = hook_input.get("stop_reason", "")
    transcript = hook_input.get("transcript", [])

    # Check for completion signals in last assistant message
    last_message = ""
    for msg in reversed(transcript):
        if msg.get("role") == "assistant":
            content = msg.get("content", "")
            if isinstance(content, list):
                # Content blocks format
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        last_message = block.get("text", "")
                        break
            else:
                last_message = str(content)
            break

    # Locate vault — try relative to CWD, then relative to this script
    vault = None
    for candidate in [
        Path.cwd() / "silver_tier",
        Path(__file__).parent.parent / "silver_tier",
        Path("D:/gold_tier/silver_tier"),
    ]:
        if candidate.exists():
            vault = candidate
            break

    if vault is None:
        # Can't find vault — allow exit
        print(json.dumps({"action": "exit"}), flush=True)
        return

    needs_action_dir = vault / "Needs_Action"
    done_dir = vault / "Done"

    if not needs_action_dir.exists():
        print(json.dumps({"action": "exit"}), flush=True)
        return

    needs_action_files = list(needs_action_dir.glob("*.md"))
    done_files = {f.name for f in done_dir.glob("*.md")} if done_dir.exists() else set()

    # Pending = in Needs_Action but NOT in Done
    pending = [f for f in needs_action_files if f.name not in done_files]

    # Explicit ALERT files should not block exit (they need human action)
    actionable_pending = [f for f in pending if not f.name.startswith("ALERT_")]

    # Allow exit conditions:
    # 1. Explicit TASK_COMPLETE signal in last message
    # 2. No pending actionable items
    # 3. Stop reason indicates tool/user interruption (not autonomous stop)
    if (
        "TASK_COMPLETE" in last_message
        or not actionable_pending
        or stop_reason in ("tool_use", "user")
    ):
        print(json.dumps({"action": "exit"}), flush=True)
    else:
        pending_names = [f.name for f in actionable_pending[:5]]
        extra = f" (+{len(actionable_pending) - 5} more)" if len(actionable_pending) > 5 else ""
        print(json.dumps({
            "action": "continue",
            "message": (
                f"Task not complete. {len(actionable_pending)} file(s) still in Needs_Action "
                f"without corresponding Done/ entries: "
                f"{', '.join(pending_names)}{extra}. "
                "Continue processing these items. When all are handled, output TASK_COMPLETE."
            ),
        }), flush=True)


if __name__ == "__main__":
    main()
