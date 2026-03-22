#!/usr/bin/env python3
"""
Browser MCP Server — browser automation via Playwright.
"""
import json
import sys
import os
from pathlib import Path
from datetime import datetime

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

VAULT_ROOT = Path("D:/gold_tier/silver_tier")
HEADLESS = os.environ.get("BROWSER_HEADLESS", "true").lower() != "false"
TIMEOUT = 30000  # ms

# ---------------------------------------------------------------------------
# Browser singleton
# ---------------------------------------------------------------------------
_playwright = None
_browser = None
_page = None


def get_page():
    """Return existing page or create a new browser/page instance."""
    global _playwright, _browser, _page

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError(
            "Playwright not installed. Run: pip install playwright && python -m playwright install chromium"
        )

    if _playwright is None:
        _playwright = sync_playwright().start()

    if _browser is None or not _browser.is_connected():
        _browser = _playwright.chromium.launch(headless=HEADLESS)

    if _page is None or _page.is_closed():
        _page = _browser.new_page()
        _page.set_default_timeout(TIMEOUT)

    return _page


def close_browser_instance():
    global _playwright, _browser, _page
    if _page and not _page.is_closed():
        _page.close()
    _page = None
    if _browser and _browser.is_connected():
        _browser.close()
    _browser = None
    if _playwright:
        _playwright.stop()
    _playwright = None


# ---------------------------------------------------------------------------
# Protocol helpers
# ---------------------------------------------------------------------------

def send(response: dict):
    print(json.dumps(response), flush=True)


def error_response(rid, code: int, message: str):
    send({"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}})


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def browser_navigate(url: str) -> str:
    try:
        page = get_page()
        page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)
        title = page.title()
        text = page.inner_text("body")[:500] if page.query_selector("body") else ""
        return f"Title: {title}\n\nContent preview:\n{text}"
    except RuntimeError as e:
        return f"ERROR: {e}"
    except Exception as e:
        return f"ERROR navigating to '{url}': {e}"


def browser_screenshot(url: str = None, save_path: str = None) -> str:
    try:
        page = get_page()

        if url:
            page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        logs_dir = VAULT_ROOT / "Logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        if save_path:
            # Validate it stays within vault
            p = Path(save_path)
            if p.is_absolute():
                return "ERROR: save_path must be relative to vault root."
            if ".." in save_path:
                return "ERROR: save_path must not contain '..'."
            target = (VAULT_ROOT / p)
            target.parent.mkdir(parents=True, exist_ok=True)
        else:
            target = logs_dir / f"screenshot_{timestamp}.png"

        page.screenshot(path=str(target))
        rel = target.relative_to(VAULT_ROOT).as_posix()
        return f"OK: Screenshot saved to vault/{rel}"
    except RuntimeError as e:
        return f"ERROR: {e}"
    except Exception as e:
        return f"ERROR taking screenshot: {e}"


def browser_click(selector: str) -> str:
    try:
        page = get_page()
        page.click(selector, timeout=TIMEOUT)
        return f"OK: Clicked element '{selector}'."
    except RuntimeError as e:
        return f"ERROR: {e}"
    except Exception as e:
        return f"ERROR clicking '{selector}': {e}"


def browser_fill_form(url: str, fields: dict) -> str:
    try:
        page = get_page()
        page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)

        filled = []
        errors = []
        for selector, value in fields.items():
            try:
                page.fill(selector, str(value), timeout=TIMEOUT)
                filled.append(selector)
            except Exception as fe:
                errors.append(f"{selector}: {fe}")

        result = f"OK: Filled {len(filled)} field(s) on {url}."
        if errors:
            result += f"\nWarnings — could not fill: {'; '.join(errors)}"
        return result
    except RuntimeError as e:
        return f"ERROR: {e}"
    except Exception as e:
        return f"ERROR filling form on '{url}': {e}"


def browser_get_text(url: str) -> str:
    try:
        page = get_page()
        page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)
        text = page.inner_text("body") if page.query_selector("body") else ""
        return text if text else "No visible text found on page."
    except RuntimeError as e:
        return f"ERROR: {e}"
    except Exception as e:
        return f"ERROR getting text from '{url}': {e}"


def browser_close() -> str:
    try:
        close_browser_instance()
        return "OK: Browser closed."
    except Exception as e:
        return f"ERROR closing browser: {e}"


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "browser_navigate",
        "description": "Navigate to a URL and return the page title and first 500 characters of text content.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to navigate to."}
            },
            "required": ["url"]
        }
    },
    {
        "name": "browser_screenshot",
        "description": "Take a screenshot of the current page (or navigate to a URL first). Saves to vault Logs/ folder.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Optional URL to navigate to before screenshotting."},
                "save_path": {"type": "string", "description": "Optional relative path within vault to save screenshot. Default: Logs/screenshot_TIMESTAMP.png."}
            },
            "required": []
        }
    },
    {
        "name": "browser_click",
        "description": "Click an element on the current page by CSS selector.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector for the element to click."}
            },
            "required": ["selector"]
        }
    },
    {
        "name": "browser_fill_form",
        "description": "Navigate to a URL and fill form fields. 'fields' is a dict mapping CSS selector to value.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to navigate to."},
                "fields": {
                    "type": "object",
                    "description": "Dictionary of {CSS_selector: value} pairs to fill.",
                    "additionalProperties": {"type": "string"}
                }
            },
            "required": ["url", "fields"]
        }
    },
    {
        "name": "browser_get_text",
        "description": "Get all visible text content from a web page.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to get text from."}
            },
            "required": ["url"]
        }
    },
    {
        "name": "browser_close",
        "description": "Close the browser and release resources.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def execute_tool(name: str, args: dict) -> str:
    try:
        if name == "browser_navigate":
            return browser_navigate(args.get("url", ""))
        elif name == "browser_screenshot":
            return browser_screenshot(args.get("url"), args.get("save_path"))
        elif name == "browser_click":
            return browser_click(args.get("selector", ""))
        elif name == "browser_fill_form":
            fields = args.get("fields", {})
            if isinstance(fields, str):
                try:
                    fields = json.loads(fields)
                except Exception:
                    fields = {}
            return browser_fill_form(args.get("url", ""), fields)
        elif name == "browser_get_text":
            return browser_get_text(args.get("url", ""))
        elif name == "browser_close":
            return browser_close()
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
                "serverInfo": {"name": "browser", "version": "1.0.0"}
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
