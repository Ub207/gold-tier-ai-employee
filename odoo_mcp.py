#!/usr/bin/env python3
"""
odoo_mcp.py — Odoo Community Integration MCP Server (stdio, JSON-RPC 2.0)

Connects to Odoo via JSON-RPC API and exposes accounting tools to Claude Code.
All write operations create DRAFT records only — nothing is auto-posted.

Config (env vars or .env file):
    ODOO_URL       = http://localhost:8069
    ODOO_DB        = odoo
    ODOO_USERNAME  = admin
    ODOO_PASSWORD  = admin
"""

import json
import os
import sys
from pathlib import Path
import urllib.request
import urllib.error
import http.cookiejar

# Load .env if present (simple parser, no dependency on python-dotenv)
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

ODOO_URL = os.environ.get("ODOO_URL", "http://localhost:8069")
ODOO_DB = os.environ.get("ODOO_DB", "odoo")
ODOO_USERNAME = os.environ.get("ODOO_USERNAME", "admin")
ODOO_PASSWORD = os.environ.get("ODOO_PASSWORD", "admin")

# ── Odoo JSON-RPC helpers ─────────────────────────────────────────────────────

# Cookie jar to maintain session across requests
_cookie_jar = http.cookiejar.CookieJar()
_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_cookie_jar))
_session_uid = None  # cached uid after authenticate


def _rpc_call(endpoint: str, payload: dict) -> dict:
    """Make a JSON-RPC call to Odoo using persistent session cookies."""
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{ODOO_URL}{endpoint}",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with _opener.open(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


def _authenticate() -> "int | str":
    """Authenticate via /web/session/authenticate and return uid (int) or error string."""
    global _session_uid
    resp = _rpc_call("/web/session/authenticate", {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "db": ODOO_DB,
            "login": ODOO_USERNAME,
            "password": ODOO_PASSWORD,
        },
    })
    if "error" in resp:
        return f"Auth error: {resp['error']}"
    result = resp.get("result", {})
    uid = result.get("uid")
    if not uid:
        return "Authentication failed — check ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD"
    _session_uid = uid
    return uid


def _execute(model: str, method: str, args: list, kwargs: dict = None) -> dict:
    """Execute an Odoo model method after authenticating."""
    uid = _authenticate()
    if isinstance(uid, str):  # error message
        return {"error": uid}

    resp = _rpc_call("/web/dataset/call_kw", {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": model,
            "method": method,
            "args": args,
            "kwargs": kwargs or {},
        },
    })
    return resp


# ── Tool implementations ──────────────────────────────────────────────────────

def odoo_get_partner(name: str) -> str:
    """Search for a customer/partner by name."""
    uid = _authenticate()
    if isinstance(uid, str):
        return f"ERROR: {uid}"

    resp = _rpc_call("/web/dataset/call_kw", {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": "res.partner",
            "method": "search_read",
            "args": [[["name", "ilike", name]]],
            "kwargs": {
                "fields": ["id", "name", "email", "phone", "street", "city", "country_id"],
                "limit": 10,
            },
        },
    })

    if "error" in resp:
        return f"ERROR: {resp['error']}"

    partners = resp.get("result", [])
    if not partners:
        return f"No partner found matching '{name}'"

    lines = [f"Found {len(partners)} partner(s) matching '{name}':\n"]
    for p in partners:
        lines.append(
            f"  ID: {p['id']} | Name: {p['name']} | "
            f"Email: {p.get('email', 'N/A')} | Phone: {p.get('phone', 'N/A')} | "
            f"City: {p.get('city', 'N/A')}"
        )
    return "\n".join(lines)


def odoo_create_invoice(partner_name: str, amount: float, description: str, currency: str = "USD") -> str:
    """Create a DRAFT invoice in Odoo. Never auto-posts."""
    uid = _authenticate()
    if isinstance(uid, str):
        return f"ERROR: {uid}"

    # Find partner
    partner_resp = _rpc_call("/web/dataset/call_kw", {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": "res.partner",
            "method": "search",
            "args": [[["name", "ilike", partner_name]]],
            "kwargs": {"limit": 1},
        },
    })
    partner_ids = partner_resp.get("result", [])
    if not partner_ids:
        return f"ERROR: Partner '{partner_name}' not found in Odoo. Create the partner first."
    partner_id = partner_ids[0]

    # Find currency
    currency_resp = _rpc_call("/web/dataset/call_kw", {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": "res.currency",
            "method": "search",
            "args": [[["name", "=", currency.upper()]]],
            "kwargs": {"limit": 1},
        },
    })
    currency_ids = currency_resp.get("result", [])
    currency_id = currency_ids[0] if currency_ids else False

    # Create draft invoice
    invoice_vals = {
        "move_type": "out_invoice",
        "partner_id": partner_id,
        "state": "draft",
        "invoice_line_ids": [
            (0, 0, {
                "name": description,
                "quantity": 1.0,
                "price_unit": float(amount),
            })
        ],
    }
    if currency_id:
        invoice_vals["currency_id"] = currency_id

    create_resp = _rpc_call("/web/dataset/call_kw", {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": "account.move",
            "method": "create",
            "args": [invoice_vals],
            "kwargs": {},
        },
    })

    if "error" in create_resp:
        return f"ERROR creating invoice: {create_resp['error']}"

    invoice_id = create_resp.get("result")
    return (
        f"DRAFT invoice created successfully.\n"
        f"  Invoice ID: {invoice_id}\n"
        f"  Partner: {partner_name} (ID: {partner_id})\n"
        f"  Amount: {amount} {currency}\n"
        f"  Description: {description}\n"
        f"  Status: DRAFT (not posted — human review required)\n"
        f"  View at: {ODOO_URL}/odoo/accounting/customer-invoices/{invoice_id}"
    )


def odoo_list_invoices(state: str = "draft", limit: int = 10) -> str:
    """List invoices filtered by state."""
    uid = _authenticate()
    if isinstance(uid, str):
        return f"ERROR: {uid}"

    domain = []
    if state and state != "all":
        domain = [["state", "=", state], ["move_type", "=", "out_invoice"]]
    else:
        domain = [["move_type", "=", "out_invoice"]]

    resp = _rpc_call("/web/dataset/call_kw", {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": "account.move",
            "method": "search_read",
            "args": [domain],
            "kwargs": {
                "fields": ["id", "name", "partner_id", "amount_total", "currency_id",
                           "state", "invoice_date", "invoice_date_due"],
                "limit": int(limit),
                "order": "invoice_date desc",
            },
        },
    })

    if "error" in resp:
        return f"ERROR: {resp['error']}"

    invoices = resp.get("result", [])
    if not invoices:
        return f"No invoices found with state='{state}'"

    lines = [f"Invoices (state={state}, showing up to {limit}):\n"]
    for inv in invoices:
        partner = inv.get("partner_id", [None, "Unknown"])
        partner_name = partner[1] if isinstance(partner, list) else str(partner)
        currency = inv.get("currency_id", [None, ""])
        currency_name = currency[1] if isinstance(currency, list) else ""
        lines.append(
            f"  #{inv['id']} | {inv.get('name', 'Draft')} | "
            f"Partner: {partner_name} | "
            f"Amount: {inv.get('amount_total', 0)} {currency_name} | "
            f"State: {inv.get('state')} | "
            f"Date: {inv.get('invoice_date', 'N/A')} | "
            f"Due: {inv.get('invoice_date_due', 'N/A')}"
        )
    return "\n".join(lines)


def odoo_list_payments(limit: int = 10) -> str:
    """List recent account payments."""
    uid = _authenticate()
    if isinstance(uid, str):
        return f"ERROR: {uid}"

    resp = _rpc_call("/web/dataset/call_kw", {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": "account.payment",
            "method": "search_read",
            "args": [[]],
            "kwargs": {
                "fields": ["id", "name", "partner_id", "amount", "currency_id",
                           "state", "date", "payment_type"],
                "limit": int(limit),
                "order": "date desc",
            },
        },
    })

    if "error" in resp:
        return f"ERROR: {resp['error']}"

    payments = resp.get("result", [])
    if not payments:
        return "No payments found."

    lines = [f"Recent Payments (up to {limit}):\n"]
    for p in payments:
        partner = p.get("partner_id", [None, "Unknown"])
        partner_name = partner[1] if isinstance(partner, list) else str(partner)
        currency = p.get("currency_id", [None, ""])
        currency_name = currency[1] if isinstance(currency, list) else ""
        lines.append(
            f"  #{p['id']} | {p.get('name', 'Payment')} | "
            f"Partner: {partner_name} | "
            f"Amount: {p.get('amount', 0)} {currency_name} | "
            f"Type: {p.get('payment_type')} | "
            f"State: {p.get('state')} | "
            f"Date: {p.get('date', 'N/A')}"
        )
    return "\n".join(lines)


def odoo_get_revenue_summary(period_days: int = 7) -> str:
    """Get revenue summary for the last N days from posted invoices."""
    uid = _authenticate()
    if isinstance(uid, str):
        return f"ERROR: {uid}"

    from datetime import datetime, timedelta
    cutoff = (datetime.now() - timedelta(days=int(period_days))).strftime("%Y-%m-%d")

    resp = _rpc_call("/web/dataset/call_kw", {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": "account.move",
            "method": "search_read",
            "args": [[
                ["move_type", "=", "out_invoice"],
                ["state", "=", "posted"],
                ["invoice_date", ">=", cutoff],
            ]],
            "kwargs": {
                "fields": ["id", "name", "partner_id", "amount_total",
                           "amount_residual", "currency_id", "invoice_date"],
                "limit": 200,
            },
        },
    })

    if "error" in resp:
        return f"ERROR: {resp['error']}"

    invoices = resp.get("result", [])
    total = sum(i.get("amount_total", 0) for i in invoices)
    outstanding = sum(i.get("amount_residual", 0) for i in invoices)
    collected = total - outstanding

    return (
        f"Revenue Summary — Last {period_days} days (since {cutoff}):\n"
        f"  Posted Invoices: {len(invoices)}\n"
        f"  Total Invoiced:  {total:.2f}\n"
        f"  Collected:       {collected:.2f}\n"
        f"  Outstanding:     {outstanding:.2f}\n"
        f"  Collection Rate: {(collected/total*100):.1f}%" if total > 0 else
        f"Revenue Summary — Last {period_days} days (since {cutoff}):\n"
        f"  No posted invoices found in this period."
    )


# ── MCP stdio server ──────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "odoo_create_invoice",
        "description": "Create a DRAFT invoice in Odoo (never auto-posted). Requires human review before posting.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "partner_name": {"type": "string", "description": "Customer/partner name"},
                "amount": {"type": "number", "description": "Invoice total amount"},
                "description": {"type": "string", "description": "Line item description"},
                "currency": {"type": "string", "description": "Currency code (default: USD)", "default": "USD"},
            },
            "required": ["partner_name", "amount", "description"],
        },
    },
    {
        "name": "odoo_list_invoices",
        "description": "List invoices filtered by state (draft, posted, cancel, all).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "state": {"type": "string", "description": "Invoice state filter", "default": "draft"},
                "limit": {"type": "integer", "description": "Max results (default 10)", "default": 10},
            },
        },
    },
    {
        "name": "odoo_get_partner",
        "description": "Search for a customer or partner by name in Odoo.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Partner name to search"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "odoo_list_payments",
        "description": "List recent account payments from Odoo.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max results (default 10)", "default": 10},
            },
        },
    },
    {
        "name": "odoo_get_revenue_summary",
        "description": "Get revenue summary for the last N days (from posted invoices).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "period_days": {"type": "integer", "description": "Number of days to look back (default 7)", "default": 7},
            },
        },
    },
]

TOOL_MAP = {
    "odoo_create_invoice": lambda a: odoo_create_invoice(
        a["partner_name"], a["amount"], a["description"], a.get("currency", "USD")
    ),
    "odoo_list_invoices": lambda a: odoo_list_invoices(
        a.get("state", "draft"), a.get("limit", 10)
    ),
    "odoo_get_partner": lambda a: odoo_get_partner(a["name"]),
    "odoo_list_payments": lambda a: odoo_list_payments(a.get("limit", 10)),
    "odoo_get_revenue_summary": lambda a: odoo_get_revenue_summary(a.get("period_days", 7)),
}


def send_response(response: dict):
    print(json.dumps(response), flush=True)


def handle_request(request: dict):
    method = request.get("method", "")
    req_id = request.get("id")

    if method == "initialize":
        send_response({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "odoo", "version": "1.0.0"},
            },
        })

    elif method == "notifications/initialized":
        pass  # No response needed

    elif method == "tools/list":
        send_response({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": TOOLS},
        })

    elif method == "tools/call":
        params = request.get("params", {})
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {})

        if tool_name not in TOOL_MAP:
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
            })
            return

        try:
            result_text = TOOL_MAP[tool_name](tool_args)
        except Exception as e:
            result_text = f"ERROR: {e}"

        send_response({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": str(result_text)}]},
        })

    else:
        if req_id is not None:
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            })


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            handle_request(request)
        except json.JSONDecodeError:
            pass
        except Exception as e:
            sys.stderr.write(f"[odoo_mcp error] {e}\n")
            sys.stderr.flush()


if __name__ == "__main__":
    main()
