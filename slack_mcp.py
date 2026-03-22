#!/usr/bin/env python3
"""
Slack MCP Server — Slack integration via slack_sdk.

Required environment variables (in D:/gold_tier/.env):
  SLACK_BOT_TOKEN   — starts with xoxb-  (send messages, upload files, etc.)
  SLACK_USER_TOKEN  — starts with xoxp-  (set_status, search_messages)
"""
import json
import sys
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Load .env from D:/gold_tier/.env
# ---------------------------------------------------------------------------
ENV_PATH = Path("D:/gold_tier/.env")

def load_env(path: Path):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val

load_env(ENV_PATH)

# ---------------------------------------------------------------------------
# Protocol helpers
# ---------------------------------------------------------------------------

def send(response: dict):
    print(json.dumps(response), flush=True)


def error_response(rid, code: int, message: str):
    send({"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}})


# ---------------------------------------------------------------------------
# Slack client helpers
# ---------------------------------------------------------------------------

def get_bot_client():
    """Return a Slack WebClient using the bot token."""
    try:
        from slack_sdk import WebClient
    except ImportError:
        raise RuntimeError(
            "slack_sdk not installed. Run: pip install slack_sdk"
        )

    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        raise RuntimeError(
            "SLACK_BOT_TOKEN not set in environment / .env file. "
            "Provide a bot token starting with xoxb-."
        )

    return WebClient(token=token)


def get_user_client():
    """Return a Slack WebClient using the user token (for status, search)."""
    try:
        from slack_sdk import WebClient
    except ImportError:
        raise RuntimeError(
            "slack_sdk not installed. Run: pip install slack_sdk"
        )

    token = os.environ.get("SLACK_USER_TOKEN", "")
    if not token:
        raise RuntimeError(
            "SLACK_USER_TOKEN not set in environment / .env file. "
            "Provide a user token starting with xoxp-."
        )

    return WebClient(token=token)


def resolve_channel(channel: str) -> str:
    """Strip leading # from channel name if present."""
    return channel.lstrip("#")


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def slack_send_message(channel: str, text: str, thread_ts: str = None) -> str:
    try:
        client = get_bot_client()
    except RuntimeError as e:
        return f"ERROR: {e}"

    try:
        kwargs = {
            "channel": resolve_channel(channel),
            "text": text
        }
        if thread_ts:
            kwargs["thread_ts"] = thread_ts

        resp = client.chat_postMessage(**kwargs)
        ts = resp.get("ts", "")
        return f"OK: Message sent to #{resolve_channel(channel)} (ts={ts})."
    except Exception as e:
        return f"ERROR sending message: {e}"


def slack_get_messages(channel: str, limit: int = 10) -> str:
    try:
        client = get_bot_client()
    except RuntimeError as e:
        return f"ERROR: {e}"

    try:
        # First resolve channel name to ID if necessary
        ch = resolve_channel(channel)
        resp = client.conversations_history(channel=ch, limit=limit)
        messages = resp.get("messages", [])

        if not messages:
            return f"No messages found in #{ch}."

        results = []
        for msg in messages:
            results.append({
                "ts": msg.get("ts", ""),
                "user": msg.get("user", msg.get("bot_id", "unknown")),
                "text": msg.get("text", ""),
                "thread_ts": msg.get("thread_ts"),
                "reply_count": msg.get("reply_count", 0)
            })

        return json.dumps(results, indent=2)
    except Exception as e:
        return f"ERROR getting messages: {e}"


def slack_list_channels() -> str:
    try:
        client = get_bot_client()
    except RuntimeError as e:
        return f"ERROR: {e}"

    try:
        results = []
        cursor = None

        while True:
            kwargs = {"exclude_archived": True, "limit": 200}
            if cursor:
                kwargs["cursor"] = cursor

            resp = client.conversations_list(**kwargs)
            channels = resp.get("channels", [])

            for ch in channels:
                results.append({
                    "id": ch.get("id", ""),
                    "name": ch.get("name", ""),
                    "is_private": ch.get("is_private", False),
                    "num_members": ch.get("num_members", 0),
                    "topic": ch.get("topic", {}).get("value", ""),
                    "purpose": ch.get("purpose", {}).get("value", "")
                })

            next_cursor = resp.get("response_metadata", {}).get("next_cursor", "")
            if not next_cursor:
                break
            cursor = next_cursor

        return json.dumps(results, indent=2)
    except Exception as e:
        return f"ERROR listing channels: {e}"


def slack_upload_file(channel: str, file_path: str, title: str = None, comment: str = None) -> str:
    try:
        client = get_bot_client()
    except RuntimeError as e:
        return f"ERROR: {e}"

    try:
        fp = Path(file_path)
        if not fp.exists():
            return f"ERROR: File not found: {file_path}"

        ch = resolve_channel(channel)
        kwargs = {
            "channels": ch,
            "file": str(fp),
            "filename": fp.name
        }
        if title:
            kwargs["title"] = title
        if comment:
            kwargs["initial_comment"] = comment

        resp = client.files_upload_v2(**kwargs)
        file_id = resp.get("file", {}).get("id", "unknown")
        return f"OK: File '{fp.name}' uploaded to #{ch} (file_id={file_id})."
    except Exception as e:
        # Fallback to older API if v2 not available
        try:
            kwargs2 = {
                "channels": resolve_channel(channel),
                "file": str(Path(file_path)),
                "filename": Path(file_path).name
            }
            if title:
                kwargs2["title"] = title
            if comment:
                kwargs2["initial_comment"] = comment
            resp2 = client.files_upload(**kwargs2)
            file_id = resp2.get("file", {}).get("id", "unknown")
            return f"OK: File '{Path(file_path).name}' uploaded to #{resolve_channel(channel)} (file_id={file_id})."
        except Exception as e2:
            return f"ERROR uploading file: {e2}"


def slack_set_status(status_text: str, status_emoji: str = ":robot_face:", duration_minutes: int = None) -> str:
    try:
        client = get_user_client()
    except RuntimeError as e:
        return f"ERROR: {e}"

    try:
        expiration = 0
        if duration_minutes and duration_minutes > 0:
            import time
            expiration = int(time.time()) + (duration_minutes * 60)

        resp = client.users_profile_set(
            profile={
                "status_text": status_text,
                "status_emoji": status_emoji,
                "status_expiration": expiration
            }
        )

        dur_info = f" (expires in {duration_minutes} min)" if duration_minutes else ""
        return f"OK: Status set to {status_emoji} '{status_text}'{dur_info}."
    except Exception as e:
        return f"ERROR setting status: {e}"


def slack_search_messages(query: str, limit: int = 10) -> str:
    try:
        client = get_user_client()
    except RuntimeError as e:
        return f"ERROR: {e}"

    try:
        resp = client.search_messages(query=query, count=limit)
        matches = resp.get("messages", {}).get("matches", [])

        if not matches:
            return f"No messages found for query: '{query}'"

        results = []
        for match in matches:
            results.append({
                "ts": match.get("ts", ""),
                "channel": match.get("channel", {}).get("name", ""),
                "user": match.get("username", ""),
                "text": match.get("text", ""),
                "permalink": match.get("permalink", "")
            })

        return json.dumps(results, indent=2)
    except Exception as e:
        return f"ERROR searching messages: {e}"


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "slack_send_message",
        "description": "Send a message to a Slack channel. Use thread_ts to reply to a thread.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel": {"type": "string", "description": "Channel name (e.g. #general or general) or channel ID."},
                "text": {"type": "string", "description": "Message text (supports Slack markdown)."},
                "thread_ts": {"type": "string", "description": "Thread timestamp to reply to. Optional."}
            },
            "required": ["channel", "text"]
        }
    },
    {
        "name": "slack_get_messages",
        "description": "Get recent messages from a Slack channel.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel": {"type": "string", "description": "Channel name or ID."},
                "limit": {"type": "integer", "description": "Number of messages to retrieve. Default 10."}
            },
            "required": ["channel"]
        }
    },
    {
        "name": "slack_list_channels",
        "description": "List all available Slack channels the bot has access to.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "slack_upload_file",
        "description": "Upload a file to a Slack channel.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel": {"type": "string", "description": "Channel name or ID."},
                "file_path": {"type": "string", "description": "Absolute path to the file to upload."},
                "title": {"type": "string", "description": "File title. Optional."},
                "comment": {"type": "string", "description": "Message to accompany the file. Optional."}
            },
            "required": ["channel", "file_path"]
        }
    },
    {
        "name": "slack_set_status",
        "description": "Set the Slack user status. Requires SLACK_USER_TOKEN.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status_text": {"type": "string", "description": "Status message text."},
                "status_emoji": {"type": "string", "description": "Emoji for status (e.g. ':robot_face:'). Default ':robot_face:'."},
                "duration_minutes": {"type": "integer", "description": "How long to set status in minutes. 0 or omit for permanent."}
            },
            "required": ["status_text"]
        }
    },
    {
        "name": "slack_search_messages",
        "description": "Search messages across the Slack workspace. Requires SLACK_USER_TOKEN.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (supports Slack search syntax, e.g. 'in:#general from:@user')."},
                "limit": {"type": "integer", "description": "Maximum results. Default 10."}
            },
            "required": ["query"]
        }
    }
]


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def execute_tool(name: str, args: dict) -> str:
    try:
        if name == "slack_send_message":
            return slack_send_message(
                args.get("channel", ""),
                args.get("text", ""),
                args.get("thread_ts")
            )
        elif name == "slack_get_messages":
            return slack_get_messages(
                args.get("channel", ""),
                int(args.get("limit", 10))
            )
        elif name == "slack_list_channels":
            return slack_list_channels()
        elif name == "slack_upload_file":
            return slack_upload_file(
                args.get("channel", ""),
                args.get("file_path", ""),
                args.get("title"),
                args.get("comment")
            )
        elif name == "slack_set_status":
            duration = args.get("duration_minutes")
            if duration is not None:
                duration = int(duration)
            return slack_set_status(
                args.get("status_text", ""),
                args.get("status_emoji", ":robot_face:"),
                duration
            )
        elif name == "slack_search_messages":
            return slack_search_messages(
                args.get("query", ""),
                int(args.get("limit", 10))
            )
        else:
            return f"ERROR: Unknown tool '{name}'."
    except Exception as e:
        return f"ERROR: Unexpected exception in tool '{name}': {e}"


def handle(request: dict):
    method = request.get("method")
    rid = request.get("id")

    if method == "initialize":
        send({
            "jsonrpc": "2.0",
            "id": rid,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "slack", "version": "1.0.0"}
            }
        })
    elif method == "notifications/initialized":
        pass
    elif method == "tools/list":
        send({"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}})
    elif method == "tools/call":
        name = request["params"]["name"]
        args = request["params"].get("arguments", {})
        result = execute_tool(name, args)
        send({
            "jsonrpc": "2.0",
            "id": rid,
            "result": {"content": [{"type": "text", "text": result}]}
        })
    elif rid is not None:
        error_response(rid, -32601, "Method not found")


if __name__ == "__main__":
    for line in sys.stdin:
        line = line.strip()
        if line:
            try:
                handle(json.loads(line))
            except Exception:
                pass
