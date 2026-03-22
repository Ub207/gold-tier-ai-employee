#!/usr/bin/env python3
"""
Email MCP Server — Gmail operations via SMTP (send) and Gmail API OAuth (read/search).
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

PROJECT_ROOT = Path("D:/gold_tier")

# ---------------------------------------------------------------------------
# Protocol helpers
# ---------------------------------------------------------------------------

def send(response: dict):
    print(json.dumps(response), flush=True)


def error_response(rid, code: int, message: str):
    send({"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}})


# ---------------------------------------------------------------------------
# Gmail API helpers (OAuth)
# ---------------------------------------------------------------------------

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
]

def get_gmail_service():
    """Return authenticated Gmail API service or raise RuntimeError with helpful message."""
    token_path = PROJECT_ROOT / "token.json"
    creds_path = PROJECT_ROOT / "credentials.json"

    if not token_path.exists():
        raise RuntimeError(
            "Gmail not authorized. token.json not found. "
            "Please complete OAuth setup: place credentials.json in D:/gold_tier/ "
            "and run the authorization flow to generate token.json."
        )

    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        creds = Credentials.from_authorized_user_file(str(token_path), GMAIL_SCOPES)

        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                token_path.write_text(creds.to_json(), encoding="utf-8")
            else:
                raise RuntimeError(
                    "Gmail credentials expired and cannot be refreshed. "
                    "Please re-run the OAuth authorization flow."
                )

        return build("gmail", "v1", credentials=creds)

    except ImportError:
        raise RuntimeError(
            "Google API libraries not installed. "
            "Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
        )


def decode_message_body(msg: dict) -> str:
    """Extract plain text body from Gmail message payload."""
    import base64

    payload = msg.get("payload", {})
    parts = payload.get("parts", [])
    body = ""

    if not parts:
        data = payload.get("body", {}).get("data", "")
        if data:
            body = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
    else:
        for part in parts:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    body = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
                    break

    return body


def get_header(headers: list, name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def send_email(to: str, subject: str, body: str, cc: str = None) -> str:
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    gmail_address = os.environ.get("GMAIL_ADDRESS", "")
    app_password = os.environ.get("GMAIL_APP_PASSWORD", "")

    if not gmail_address:
        return "ERROR: GMAIL_ADDRESS not set in environment / .env file."
    if not app_password:
        return "ERROR: GMAIL_APP_PASSWORD not set in environment / .env file."

    try:
        msg = MIMEMultipart()
        msg["From"] = gmail_address
        msg["To"] = to
        msg["Subject"] = subject
        if cc:
            msg["Cc"] = cc
        msg.attach(MIMEText(body, "plain", "utf-8"))

        recipients = [to]
        if cc:
            recipients.extend([addr.strip() for addr in cc.split(",")])

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(gmail_address, app_password)
            smtp.sendmail(gmail_address, recipients, msg.as_string())

        cc_info = f" (cc: {cc})" if cc else ""
        return f"OK: Email sent to {to}{cc_info} with subject '{subject}'."
    except Exception as e:
        return f"ERROR sending email: {e}"


def read_emails(max_results: int = 5, query: str = "is:unread") -> str:
    try:
        service = get_gmail_service()
    except RuntimeError as e:
        return f"ERROR: {e}"

    try:
        response = service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()

        messages = response.get("messages", [])
        if not messages:
            return f"No emails found for query: '{query}'"

        results = []
        for msg_ref in messages:
            msg = service.users().messages().get(
                userId="me", id=msg_ref["id"], format="full"
            ).execute()
            headers = msg.get("payload", {}).get("headers", [])
            results.append({
                "id": msg["id"],
                "from": get_header(headers, "From"),
                "to": get_header(headers, "To"),
                "subject": get_header(headers, "Subject"),
                "date": get_header(headers, "Date"),
                "snippet": msg.get("snippet", ""),
                "body_preview": decode_message_body(msg)[:500]
            })

        return json.dumps(results, indent=2)
    except Exception as e:
        return f"ERROR reading emails: {e}"


def search_emails(query: str, max_results: int = 10) -> str:
    try:
        service = get_gmail_service()
    except RuntimeError as e:
        return f"ERROR: {e}"

    try:
        response = service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()

        messages = response.get("messages", [])
        if not messages:
            return f"No emails found for query: '{query}'"

        results = []
        for msg_ref in messages:
            msg = service.users().messages().get(
                userId="me", id=msg_ref["id"], format="metadata",
                metadataHeaders=["From", "To", "Subject", "Date"]
            ).execute()
            headers = msg.get("payload", {}).get("headers", [])
            results.append({
                "id": msg["id"],
                "from": get_header(headers, "From"),
                "subject": get_header(headers, "Subject"),
                "date": get_header(headers, "Date"),
                "snippet": msg.get("snippet", "")
            })

        return json.dumps(results, indent=2)
    except Exception as e:
        return f"ERROR searching emails: {e}"


def mark_read(message_id: str) -> str:
    try:
        service = get_gmail_service()
    except RuntimeError as e:
        return f"ERROR: {e}"

    try:
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"removeLabelIds": ["UNREAD"]}
        ).execute()
        return f"OK: Message {message_id} marked as read."
    except Exception as e:
        return f"ERROR marking message as read: {e}"


def create_draft(to: str, subject: str, body: str) -> str:
    try:
        service = get_gmail_service()
    except RuntimeError as e:
        return f"ERROR: {e}"

    try:
        import base64
        from email.mime.text import MIMEText

        msg = MIMEText(body, "plain", "utf-8")
        msg["To"] = to
        msg["Subject"] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

        draft = service.users().drafts().create(
            userId="me",
            body={"message": {"raw": raw}}
        ).execute()

        return f"OK: Draft created with ID {draft['id']} (to: {to}, subject: '{subject}')."
    except Exception as e:
        return f"ERROR creating draft: {e}"


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "send_email",
        "description": "Send an email via Gmail SMTP. Requires GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address."},
                "subject": {"type": "string", "description": "Email subject."},
                "body": {"type": "string", "description": "Email body text."},
                "cc": {"type": "string", "description": "CC email address(es), comma-separated. Optional."}
            },
            "required": ["to", "subject", "body"]
        }
    },
    {
        "name": "read_emails",
        "description": "Read emails from Gmail inbox via OAuth. Requires token.json in D:/gold_tier/.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "max_results": {"type": "integer", "description": "Maximum number of emails to return. Default 5."},
                "query": {"type": "string", "description": "Gmail search query. Default 'is:unread'."}
            },
            "required": []
        }
    },
    {
        "name": "search_emails",
        "description": "Search Gmail messages using Gmail search syntax.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Gmail search query (e.g. 'from:boss@example.com subject:report')."},
                "max_results": {"type": "integer", "description": "Maximum results. Default 10."}
            },
            "required": ["query"]
        }
    },
    {
        "name": "mark_read",
        "description": "Mark an email as read by message ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message_id": {"type": "string", "description": "Gmail message ID."}
            },
            "required": ["message_id"]
        }
    },
    {
        "name": "create_draft",
        "description": "Create a Gmail draft (does not send). Requires OAuth token.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address."},
                "subject": {"type": "string", "description": "Email subject."},
                "body": {"type": "string", "description": "Email body text."}
            },
            "required": ["to", "subject", "body"]
        }
    }
]


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def execute_tool(name: str, args: dict) -> str:
    try:
        if name == "send_email":
            return send_email(
                args.get("to", ""),
                args.get("subject", ""),
                args.get("body", ""),
                args.get("cc")
            )
        elif name == "read_emails":
            return read_emails(
                int(args.get("max_results", 5)),
                args.get("query", "is:unread")
            )
        elif name == "search_emails":
            return search_emails(
                args.get("query", ""),
                int(args.get("max_results", 10))
            )
        elif name == "mark_read":
            return mark_read(args.get("message_id", ""))
        elif name == "create_draft":
            return create_draft(
                args.get("to", ""),
                args.get("subject", ""),
                args.get("body", "")
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
                "serverInfo": {"name": "email", "version": "1.0.0"}
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
