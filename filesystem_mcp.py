#!/usr/bin/env python3
"""
Filesystem MCP Server — vault file operations.
Vault root: D:/gold_tier/silver_tier/
"""
import json
import sys
import os
import shutil
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Vault root
# ---------------------------------------------------------------------------
VAULT_ROOT = Path("D:/gold_tier/silver_tier")

# ---------------------------------------------------------------------------
# Protocol helpers
# ---------------------------------------------------------------------------

def send(response: dict):
    print(json.dumps(response), flush=True)


def error_response(rid, code: int, message: str):
    send({"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}})


def ok_response(rid, text: str):
    send({
        "jsonrpc": "2.0",
        "id": rid,
        "result": {
            "content": [{"type": "text", "text": text}]
        }
    })


# ---------------------------------------------------------------------------
# Path safety
# ---------------------------------------------------------------------------

def safe_resolve(rel_path: str) -> Path | None:
    """Resolve a relative path inside the vault. Returns None if unsafe."""
    if not rel_path:
        return None
    # Reject obvious absolute paths and traversal attempts
    if ".." in rel_path:
        return None
    p = Path(rel_path)
    if p.is_absolute():
        return None
    resolved = (VAULT_ROOT / p).resolve()
    try:
        resolved.relative_to(VAULT_ROOT.resolve())
    except ValueError:
        return None
    return resolved


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def read_file(path: str) -> str:
    if ".." in path or Path(path).is_absolute():
        return "ERROR: Path must be relative and must not contain '..'."
    target = safe_resolve(path)
    if target is None:
        return "ERROR: Invalid or unsafe path."
    if not target.exists():
        return f"ERROR: File not found: {path}"
    if not target.is_file():
        return f"ERROR: Path is not a file: {path}"
    try:
        return target.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"ERROR reading file: {e}"


def write_file(path: str, content: str) -> str:
    if ".." in path or Path(path).is_absolute():
        return "ERROR: Path must be relative and must not contain '..'."
    target = safe_resolve(path)
    if target is None:
        return "ERROR: Invalid or unsafe path."
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"OK: File written to {path} ({len(content)} chars)."
    except Exception as e:
        return f"ERROR writing file: {e}"


def list_folder(path: str) -> str:
    rel = path if path else ""
    if ".." in rel or (rel and Path(rel).is_absolute()):
        return "ERROR: Path must be relative and must not contain '..'."
    if rel:
        target = safe_resolve(rel)
    else:
        target = VAULT_ROOT
    if target is None:
        return "ERROR: Invalid or unsafe path."
    if not target.exists():
        return f"ERROR: Folder not found: {path}"
    if not target.is_dir():
        return f"ERROR: Path is not a directory: {path}"
    try:
        items = []
        for entry in sorted(target.iterdir()):
            mtime = datetime.fromtimestamp(entry.stat().st_mtime).isoformat()
            items.append({
                "name": entry.name,
                "type": "directory" if entry.is_dir() else "file",
                "modified": mtime
            })
        return json.dumps(items, indent=2)
    except Exception as e:
        return f"ERROR listing folder: {e}"


def move_file(from_path: str, to_path: str) -> str:
    if ".." in from_path or ".." in to_path:
        return "ERROR: Paths must not contain '..'."
    if Path(from_path).is_absolute() or Path(to_path).is_absolute():
        return "ERROR: Paths must be relative."
    src = safe_resolve(from_path)
    dst = safe_resolve(to_path)
    if src is None or dst is None:
        return "ERROR: Invalid or unsafe path."
    if not src.exists():
        return f"ERROR: Source not found: {from_path}"
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return f"OK: Moved '{from_path}' → '{to_path}'."
    except Exception as e:
        return f"ERROR moving file: {e}"


def create_action_file(filename: str, content: str) -> str:
    if ".." in filename or "/" in filename or "\\" in filename:
        return "ERROR: filename must be a plain filename with no path separators or '..'."
    action_dir = VAULT_ROOT / "Needs_Action"
    try:
        action_dir.mkdir(parents=True, exist_ok=True)
        target = action_dir / filename
        target.write_text(content, encoding="utf-8")
        return f"OK: Action file created at Needs_Action/{filename}."
    except Exception as e:
        return f"ERROR creating action file: {e}"


def search_vault(query: str) -> str:
    if not query:
        return "ERROR: Query string is required."
    results = []
    try:
        for md_file in VAULT_ROOT.rglob("*.md"):
            try:
                lines = md_file.read_text(encoding="utf-8", errors="replace").splitlines()
                for i, line in enumerate(lines, start=1):
                    if query.lower() in line.lower():
                        rel = md_file.relative_to(VAULT_ROOT).as_posix()
                        results.append({
                            "file": rel,
                            "line_number": i,
                            "excerpt": line.strip()[:200]
                        })
            except Exception:
                continue
        if not results:
            return f"No matches found for query: '{query}'"
        return json.dumps(results, indent=2)
    except Exception as e:
        return f"ERROR searching vault: {e}"


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "read_file",
        "description": "Read a file from the vault. Path is relative to vault root (D:/gold_tier/silver_tier/).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative file path within the vault."}
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Write or overwrite a file in the vault. Creates parent directories as needed.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative file path within the vault."},
                "content": {"type": "string", "description": "File content to write."}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "list_folder",
        "description": "List files and folders inside a vault directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative folder path within the vault. Empty string for vault root."}
            },
            "required": []
        }
    },
    {
        "name": "move_file",
        "description": "Move or rename a file within the vault.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "from_path": {"type": "string", "description": "Source relative path."},
                "to_path": {"type": "string", "description": "Destination relative path."}
            },
            "required": ["from_path", "to_path"]
        }
    },
    {
        "name": "create_action_file",
        "description": "Create a file in the Needs_Action/ folder of the vault.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Plain filename (no path separators)."},
                "content": {"type": "string", "description": "File content."}
            },
            "required": ["filename", "content"]
        }
    },
    {
        "name": "search_vault",
        "description": "Search all markdown files in the vault for a query string. Returns matching lines with file and line number.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search string (case-insensitive)."}
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
        if name == "read_file":
            return read_file(args.get("path", ""))
        elif name == "write_file":
            return write_file(args.get("path", ""), args.get("content", ""))
        elif name == "list_folder":
            return list_folder(args.get("path", ""))
        elif name == "move_file":
            return move_file(args.get("from_path", ""), args.get("to_path", ""))
        elif name == "create_action_file":
            return create_action_file(args.get("filename", ""), args.get("content", ""))
        elif name == "search_vault":
            return search_vault(args.get("query", ""))
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
                "serverInfo": {"name": "filesystem", "version": "1.0.0"}
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
