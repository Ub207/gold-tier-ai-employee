#!/usr/bin/env python3
"""
Calendar MCP Server — Google Calendar integration via OAuth2.

Authentication:
  python calendar_mcp.py --auth
  (Runs the OAuth flow and saves token.json in D:/gold_tier/)
"""
import json
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone

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

PROJECT_ROOT = Path("D:/gold_tier")

# ---------------------------------------------------------------------------
# Protocol helpers
# ---------------------------------------------------------------------------

def send(response: dict):
    print(json.dumps(response), flush=True)


def error_response(rid, code: int, message: str):
    send({"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}})


# ---------------------------------------------------------------------------
# Google Calendar API helpers
# ---------------------------------------------------------------------------

CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
]

NOT_AUTH_MSG = (
    "Calendar not authorized. Run: python calendar_mcp.py --auth\n"
    "Ensure credentials.json is in D:/gold_tier/ before running."
)


def get_calendar_service():
    """Return authenticated Google Calendar service or raise RuntimeError."""
    token_path = PROJECT_ROOT / "token.json"
    creds_path = PROJECT_ROOT / "credentials.json"

    if not token_path.exists():
        raise RuntimeError(NOT_AUTH_MSG)

    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        creds = Credentials.from_authorized_user_file(str(token_path), CALENDAR_SCOPES)

        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                token_path.write_text(creds.to_json(), encoding="utf-8")
            else:
                raise RuntimeError(NOT_AUTH_MSG)

        return build("calendar", "v3", credentials=creds)

    except ImportError:
        raise RuntimeError(
            "Google API libraries not installed. "
            "Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
        )


def run_auth_flow():
    """Run the OAuth flow interactively and save token.json."""
    creds_path = PROJECT_ROOT / "credentials.json"
    token_path = PROJECT_ROOT / "token.json"

    if not creds_path.exists():
        print(f"ERROR: credentials.json not found at {creds_path}", flush=True)
        sys.exit(1)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials

        creds = None
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), CALENDAR_SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), CALENDAR_SCOPES)
                creds = flow.run_local_server(port=0)
            token_path.write_text(creds.to_json(), encoding="utf-8")

        print(f"Authorization successful! token.json saved to {token_path}", flush=True)
    except ImportError:
        print(
            "Google auth libraries not installed.\n"
            "Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib",
            flush=True
        )
        sys.exit(1)
    except Exception as e:
        print(f"Authorization failed: {e}", flush=True)
        sys.exit(1)


def format_event(event: dict) -> dict:
    start = event.get("start", {})
    end = event.get("end", {})
    return {
        "id": event.get("id", ""),
        "title": event.get("summary", "(no title)"),
        "start": start.get("dateTime", start.get("date", "")),
        "end": end.get("dateTime", end.get("date", "")),
        "description": event.get("description", ""),
        "location": event.get("location", "")
    }


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def list_events(days_ahead: int = 7, calendar_id: str = "primary") -> str:
    try:
        service = get_calendar_service()
    except RuntimeError as e:
        return f"ERROR: {e}"

    try:
        now = datetime.now(timezone.utc)
        time_max = now + timedelta(days=days_ahead)

        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=now.isoformat(),
            timeMax=time_max.isoformat(),
            maxResults=50,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        events = events_result.get("items", [])
        if not events:
            return f"No events found in the next {days_ahead} days."

        return json.dumps([format_event(e) for e in events], indent=2)
    except Exception as e:
        return f"ERROR listing events: {e}"


def create_event(
    title: str,
    start_datetime: str,
    end_datetime: str,
    description: str = None,
    location: str = None,
    calendar_id: str = "primary"
) -> str:
    try:
        service = get_calendar_service()
    except RuntimeError as e:
        return f"ERROR: {e}"

    try:
        body = {
            "summary": title,
            "start": {"dateTime": start_datetime},
            "end": {"dateTime": end_datetime},
        }
        if description:
            body["description"] = description
        if location:
            body["location"] = location

        event = service.events().insert(calendarId=calendar_id, body=body).execute()
        return f"OK: Event created — ID: {event['id']}, title: '{title}', start: {start_datetime}."
    except Exception as e:
        return f"ERROR creating event: {e}"


def update_event(
    event_id: str,
    title: str = None,
    start_datetime: str = None,
    end_datetime: str = None,
    description: str = None,
    calendar_id: str = "primary"
) -> str:
    try:
        service = get_calendar_service()
    except RuntimeError as e:
        return f"ERROR: {e}"

    try:
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()

        if title is not None:
            event["summary"] = title
        if start_datetime is not None:
            event["start"] = {"dateTime": start_datetime}
        if end_datetime is not None:
            event["end"] = {"dateTime": end_datetime}
        if description is not None:
            event["description"] = description

        updated = service.events().update(
            calendarId=calendar_id, eventId=event_id, body=event
        ).execute()

        return f"OK: Event {event_id} updated. New title: '{updated.get('summary', '')}'."
    except Exception as e:
        return f"ERROR updating event: {e}"


def delete_event(event_id: str, calendar_id: str = "primary") -> str:
    try:
        service = get_calendar_service()
    except RuntimeError as e:
        return f"ERROR: {e}"

    try:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        return f"OK: Event {event_id} deleted."
    except Exception as e:
        return f"ERROR deleting event: {e}"


def find_free_slots(date: str, duration_minutes: int = 60, calendar_id: str = "primary") -> str:
    try:
        service = get_calendar_service()
    except RuntimeError as e:
        return f"ERROR: {e}"

    try:
        # Parse the date
        day = datetime.fromisoformat(date).date()
        day_start = datetime(day.year, day.month, day.day, 8, 0, 0, tzinfo=timezone.utc)
        day_end = datetime(day.year, day.month, day.day, 18, 0, 0, tzinfo=timezone.utc)

        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=day_start.isoformat(),
            timeMax=day_end.isoformat(),
            maxResults=50,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        events = events_result.get("items", [])

        # Build busy intervals
        busy = []
        for ev in events:
            s = ev.get("start", {})
            e = ev.get("end", {})
            s_str = s.get("dateTime", s.get("date"))
            e_str = e.get("dateTime", e.get("date"))
            if s_str and e_str:
                try:
                    busy.append((
                        datetime.fromisoformat(s_str.replace("Z", "+00:00")),
                        datetime.fromisoformat(e_str.replace("Z", "+00:00"))
                    ))
                except Exception:
                    continue

        busy.sort(key=lambda x: x[0])

        # Find free slots
        free_slots = []
        cursor = day_start
        delta = timedelta(minutes=duration_minutes)

        for b_start, b_end in busy:
            while cursor + delta <= b_start:
                free_slots.append({
                    "start": cursor.isoformat(),
                    "end": (cursor + delta).isoformat()
                })
                cursor += delta
            if b_end > cursor:
                cursor = b_end

        while cursor + delta <= day_end:
            free_slots.append({
                "start": cursor.isoformat(),
                "end": (cursor + delta).isoformat()
            })
            cursor += delta

        if not free_slots:
            return f"No free {duration_minutes}-minute slots found on {date} between 08:00 and 18:00."

        return json.dumps(free_slots, indent=2)
    except Exception as e:
        return f"ERROR finding free slots: {e}"


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "list_events",
        "description": "List upcoming Google Calendar events.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "days_ahead": {"type": "integer", "description": "Number of days ahead to look. Default 7."},
                "calendar_id": {"type": "string", "description": "Calendar ID. Default 'primary'."}
            },
            "required": []
        }
    },
    {
        "name": "create_event",
        "description": "Create a Google Calendar event.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Event title."},
                "start_datetime": {"type": "string", "description": "ISO8601 start datetime (e.g. 2024-12-25T10:00:00+02:00)."},
                "end_datetime": {"type": "string", "description": "ISO8601 end datetime."},
                "description": {"type": "string", "description": "Event description. Optional."},
                "location": {"type": "string", "description": "Event location. Optional."},
                "calendar_id": {"type": "string", "description": "Calendar ID. Default 'primary'."}
            },
            "required": ["title", "start_datetime", "end_datetime"]
        }
    },
    {
        "name": "update_event",
        "description": "Update an existing Google Calendar event. Only provide fields to change.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "Google Calendar event ID."},
                "title": {"type": "string", "description": "New title. Optional."},
                "start_datetime": {"type": "string", "description": "New ISO8601 start datetime. Optional."},
                "end_datetime": {"type": "string", "description": "New ISO8601 end datetime. Optional."},
                "description": {"type": "string", "description": "New description. Optional."},
                "calendar_id": {"type": "string", "description": "Calendar ID. Default 'primary'."}
            },
            "required": ["event_id"]
        }
    },
    {
        "name": "delete_event",
        "description": "Delete a Google Calendar event by ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "Google Calendar event ID."},
                "calendar_id": {"type": "string", "description": "Calendar ID. Default 'primary'."}
            },
            "required": ["event_id"]
        }
    },
    {
        "name": "find_free_slots",
        "description": "Find free time slots on a given date (checks 08:00–18:00 UTC).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Date in YYYY-MM-DD format."},
                "duration_minutes": {"type": "integer", "description": "Slot duration in minutes. Default 60."},
                "calendar_id": {"type": "string", "description": "Calendar ID. Default 'primary'."}
            },
            "required": ["date"]
        }
    }
]


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def execute_tool(name: str, args: dict) -> str:
    try:
        if name == "list_events":
            return list_events(
                int(args.get("days_ahead", 7)),
                args.get("calendar_id", "primary")
            )
        elif name == "create_event":
            return create_event(
                args.get("title", ""),
                args.get("start_datetime", ""),
                args.get("end_datetime", ""),
                args.get("description"),
                args.get("location"),
                args.get("calendar_id", "primary")
            )
        elif name == "update_event":
            return update_event(
                args.get("event_id", ""),
                args.get("title"),
                args.get("start_datetime"),
                args.get("end_datetime"),
                args.get("description"),
                args.get("calendar_id", "primary")
            )
        elif name == "delete_event":
            return delete_event(
                args.get("event_id", ""),
                args.get("calendar_id", "primary")
            )
        elif name == "find_free_slots":
            return find_free_slots(
                args.get("date", ""),
                int(args.get("duration_minutes", 60)),
                args.get("calendar_id", "primary")
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
                "serverInfo": {"name": "calendar", "version": "1.0.0"}
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
    if "--auth" in sys.argv:
        run_auth_flow()
    else:
        for line in sys.stdin:
            line = line.strip()
            if line:
                try:
                    handle(json.loads(line))
                except Exception:
                    pass
