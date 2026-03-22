#!/usr/bin/env python3
"""
facebook_instagram_mcp.py — Facebook + Instagram MCP Server (stdio, JSON-RPC 2.0)

Uses Facebook Graph API for both Facebook Pages and Instagram Business accounts.

Config (env vars or .env file):
    FACEBOOK_ACCESS_TOKEN  — Page Access Token (long-lived preferred)
    FACEBOOK_PAGE_ID       — Facebook Page ID (default page)
    INSTAGRAM_USER_ID      — Instagram Business Account User ID
"""

import json
import os
import sys
import urllib.request
import urllib.parse
from pathlib import Path

# Load .env dynamically (re-reads on every call so token updates take effect without restart)
_env_path = Path(__file__).parent / ".env"

def _load_env():
    if _env_path.exists():
        for _line in _env_path.read_text(encoding="utf-8").splitlines():
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ[_k.strip()] = _v.strip()

def _get_token():
    _load_env()
    return os.environ.get("FACEBOOK_ACCESS_TOKEN", "")

def _get_page_id():
    return os.environ.get("FACEBOOK_PAGE_ID", "")

def _get_ig_user_id():
    return os.environ.get("INSTAGRAM_USER_ID", "")

FACEBOOK_PAGE_ID = ""
INSTAGRAM_USER_ID = ""

GRAPH_API_BASE = "https://graph.facebook.com/v19.0"

_NOT_CONFIGURED_MSG = (
    "Facebook/Instagram credentials not configured. "
    "Set FACEBOOK_ACCESS_TOKEN (and optionally FACEBOOK_PAGE_ID, INSTAGRAM_USER_ID) "
    "in your .env file. Get credentials at: https://developers.facebook.com/"
)


def _graph_get(path: str, params: dict = None) -> dict:
    """Make a GET request to the Graph API."""
    token = _get_token()
    if not token:
        return {"error": _NOT_CONFIGURED_MSG}
    p = params or {}
    p["access_token"] = token
    query = urllib.parse.urlencode(p)
    url = f"{GRAPH_API_BASE}/{path}?{query}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return {"error": json.loads(body)}
        except Exception:
            return {"error": body}
    except Exception as e:
        return {"error": str(e)}


def _graph_post(path: str, data: dict) -> dict:
    """Make a POST request to the Graph API."""
    token = _get_token()
    if not token:
        return {"error": _NOT_CONFIGURED_MSG}
    data["access_token"] = token
    body = urllib.parse.urlencode(data).encode("utf-8")
    url = f"{GRAPH_API_BASE}/{path}"
    try:
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_err = e.read().decode("utf-8")
        try:
            return {"error": json.loads(body_err)}
        except Exception:
            return {"error": body_err}
    except Exception as e:
        return {"error": str(e)}


# ── Tool implementations ──────────────────────────────────────────────────────

def facebook_post(message: str, page_id: str = None) -> str:
    """Post a message to a Facebook Page."""
    if not _get_token():
        return f"ERROR: {_NOT_CONFIGURED_MSG}"

    pid = page_id or _get_page_id()
    if not pid:
        return (
            "ERROR: No page_id provided and FACEBOOK_PAGE_ID not set in .env. "
            "Pass page_id parameter or set FACEBOOK_PAGE_ID env var."
        )

    result = _graph_post(f"{pid}/feed", {"message": message})

    if "error" in result:
        err = result["error"]
        if isinstance(err, dict):
            return f"ERROR posting to Facebook: {err.get('message', err)}"
        return f"ERROR posting to Facebook: {err}"

    post_id = result.get("id", "unknown")
    return (
        f"Facebook post published successfully!\n"
        f"  Post ID: {post_id}\n"
        f"  Page: {pid}\n"
        f"  Preview: {message[:100]}{'...' if len(message) > 100 else ''}\n"
        f"  URL: https://www.facebook.com/{post_id.replace('_', '/posts/')}"
    )


def facebook_get_page_posts(page_id: str = None, limit: int = 5) -> str:
    """Get recent posts from a Facebook Page."""
    if not _get_token():
        return f"ERROR: {_NOT_CONFIGURED_MSG}"

    pid = page_id or FACEBOOK_PAGE_ID
    if not pid:
        return "ERROR: No page_id provided and FACEBOOK_PAGE_ID not set."

    result = _graph_get(f"{pid}/feed", {
        "fields": "id,message,created_time,likes.summary(true),comments.summary(true)",
        "limit": str(int(limit)),
    })

    if "error" in result:
        err = result["error"]
        if isinstance(err, dict):
            return f"ERROR fetching page posts: {err.get('message', err)}"
        return f"ERROR fetching page posts: {err}"

    posts = result.get("data", [])
    if not posts:
        return f"No posts found for page {pid}"

    lines = [f"Recent posts from page {pid} ({len(posts)} posts):\n"]
    for p in posts:
        msg = p.get("message", "[No text]")
        likes = p.get("likes", {}).get("summary", {}).get("total_count", 0)
        comments = p.get("comments", {}).get("summary", {}).get("total_count", 0)
        lines.append(
            f"  [{p.get('created_time', 'N/A')}] ID: {p['id']}\n"
            f"    {msg[:120]}{'...' if len(msg) > 120 else ''}\n"
            f"    Likes: {likes} | Comments: {comments}"
        )
    return "\n".join(lines)


def instagram_post_image(image_url: str, caption: str, ig_user_id: str = None) -> str:
    """
    Post an image to Instagram Business account.
    Two-step: create media container, then publish.
    """
    if not _get_token():
        return f"ERROR: {_NOT_CONFIGURED_MSG}"

    uid = ig_user_id or INSTAGRAM_USER_ID
    if not uid:
        return (
            "ERROR: No ig_user_id provided and INSTAGRAM_USER_ID not set in .env."
        )

    # Step 1: Create media container
    container = _graph_post(f"{uid}/media", {
        "image_url": image_url,
        "caption": caption,
    })

    if "error" in container:
        err = container["error"]
        if isinstance(err, dict):
            return f"ERROR creating Instagram media container: {err.get('message', err)}"
        return f"ERROR creating Instagram media container: {err}"

    container_id = container.get("id")
    if not container_id:
        return "ERROR: Instagram media container creation returned no ID."

    # Step 2: Publish
    publish = _graph_post(f"{uid}/media_publish", {"creation_id": container_id})

    if "error" in publish:
        err = publish["error"]
        if isinstance(err, dict):
            return f"ERROR publishing Instagram post: {err.get('message', err)}"
        return f"ERROR publishing Instagram post: {err}"

    media_id = publish.get("id", "unknown")
    return (
        f"Instagram post published successfully!\n"
        f"  Media ID: {media_id}\n"
        f"  Caption: {caption[:100]}{'...' if len(caption) > 100 else ''}\n"
        f"  Image URL: {image_url}"
    )


def instagram_get_posts(ig_user_id: str = None, limit: int = 5) -> str:
    """Get recent Instagram posts for a business account."""
    if not _get_token():
        return f"ERROR: {_NOT_CONFIGURED_MSG}"

    uid = ig_user_id or INSTAGRAM_USER_ID
    if not uid:
        return "ERROR: No ig_user_id provided and INSTAGRAM_USER_ID not set."

    result = _graph_get(f"{uid}/media", {
        "fields": "id,caption,media_type,timestamp,like_count,comments_count,permalink",
        "limit": str(int(limit)),
    })

    if "error" in result:
        err = result["error"]
        if isinstance(err, dict):
            return f"ERROR fetching Instagram posts: {err.get('message', err)}"
        return f"ERROR fetching Instagram posts: {err}"

    posts = result.get("data", [])
    if not posts:
        return f"No Instagram posts found for account {uid}"

    lines = [f"Recent Instagram posts for {uid} ({len(posts)} posts):\n"]
    for p in posts:
        caption = p.get("caption", "[No caption]")
        lines.append(
            f"  [{p.get('timestamp', 'N/A')}] ID: {p['id']} | Type: {p.get('media_type')}\n"
            f"    {caption[:120]}{'...' if len(caption) > 120 else ''}\n"
            f"    Likes: {p.get('like_count', 0)} | Comments: {p.get('comments_count', 0)}\n"
            f"    URL: {p.get('permalink', 'N/A')}"
        )
    return "\n".join(lines)


def get_social_summary() -> str:
    """Get engagement summary across configured Facebook page and Instagram account."""
    if not _get_token():
        return f"ERROR: {_NOT_CONFIGURED_MSG}"

    lines = ["Social Media Engagement Summary\n" + "=" * 40 + "\n"]

    # Facebook page summary
    if FACEBOOK_PAGE_ID:
        page_info = _graph_get(FACEBOOK_PAGE_ID, {
            "fields": "name,fan_count,followers_count,posts.limit(5){id,message,likes.summary(true),created_time}",
        })
        if "error" not in page_info:
            lines.append(f"FACEBOOK PAGE: {page_info.get('name', FACEBOOK_PAGE_ID)}")
            lines.append(f"  Fans/Likes: {page_info.get('fan_count', 'N/A')}")
            lines.append(f"  Followers: {page_info.get('followers_count', 'N/A')}")
            posts = page_info.get("posts", {}).get("data", [])
            total_likes = sum(
                p.get("likes", {}).get("summary", {}).get("total_count", 0)
                for p in posts
            )
            lines.append(f"  Recent 5 posts total likes: {total_likes}")
        else:
            lines.append(f"Facebook: Could not fetch page data — {page_info['error']}")
    else:
        lines.append("Facebook: FACEBOOK_PAGE_ID not set")

    lines.append("")

    # Instagram summary
    if INSTAGRAM_USER_ID:
        ig_info = _graph_get(INSTAGRAM_USER_ID, {
            "fields": "username,followers_count,media_count,media.limit(5){like_count,comments_count}",
        })
        if "error" not in ig_info:
            lines.append(f"INSTAGRAM: @{ig_info.get('username', INSTAGRAM_USER_ID)}")
            lines.append(f"  Followers: {ig_info.get('followers_count', 'N/A')}")
            lines.append(f"  Total Posts: {ig_info.get('media_count', 'N/A')}")
            media = ig_info.get("media", {}).get("data", [])
            total_likes = sum(m.get("like_count", 0) for m in media)
            total_comments = sum(m.get("comments_count", 0) for m in media)
            lines.append(f"  Recent 5 posts: {total_likes} likes, {total_comments} comments")
        else:
            lines.append(f"Instagram: Could not fetch data — {ig_info['error']}")
    else:
        lines.append("Instagram: INSTAGRAM_USER_ID not set")

    return "\n".join(lines)


# ── MCP stdio server ──────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "facebook_post",
        "description": "Post a text message to a Facebook Page.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Post text content"},
                "page_id": {"type": "string", "description": "Facebook Page ID (uses FACEBOOK_PAGE_ID env var if not provided)"},
            },
            "required": ["message"],
        },
    },
    {
        "name": "facebook_get_page_posts",
        "description": "Get recent posts from a Facebook Page with engagement metrics.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "Facebook Page ID"},
                "limit": {"type": "integer", "description": "Max posts to return (default 5)", "default": 5},
            },
        },
    },
    {
        "name": "instagram_post_image",
        "description": "Post an image to an Instagram Business account.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "image_url": {"type": "string", "description": "Public URL of the image to post"},
                "caption": {"type": "string", "description": "Post caption/text"},
                "ig_user_id": {"type": "string", "description": "Instagram Business User ID (uses INSTAGRAM_USER_ID env var if not provided)"},
            },
            "required": ["image_url", "caption"],
        },
    },
    {
        "name": "instagram_get_posts",
        "description": "Get recent Instagram posts with engagement metrics.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ig_user_id": {"type": "string", "description": "Instagram Business User ID"},
                "limit": {"type": "integer", "description": "Max posts to return (default 5)", "default": 5},
            },
        },
    },
    {
        "name": "get_social_summary",
        "description": "Get a combined engagement summary for configured Facebook page and Instagram account.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]

TOOL_MAP = {
    "facebook_post": lambda a: facebook_post(a["message"], a.get("page_id")),
    "facebook_get_page_posts": lambda a: facebook_get_page_posts(a.get("page_id"), a.get("limit", 5)),
    "instagram_post_image": lambda a: instagram_post_image(a["image_url"], a["caption"], a.get("ig_user_id")),
    "instagram_get_posts": lambda a: instagram_get_posts(a.get("ig_user_id"), a.get("limit", 5)),
    "get_social_summary": lambda a: get_social_summary(),
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
                "serverInfo": {"name": "facebook-instagram", "version": "1.0.0"},
            },
        })

    elif method == "notifications/initialized":
        pass

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
            sys.stderr.write(f"[facebook_instagram_mcp error] {e}\n")
            sys.stderr.flush()


if __name__ == "__main__":
    main()
