#!/usr/bin/env python3
"""
twitter_mcp.py — Twitter/X MCP Server (stdio, JSON-RPC 2.0)

Uses Twitter API v2 via Tweepy (if installed) or direct HTTP requests.

Config (env vars or .env file):
    TWITTER_API_KEY
    TWITTER_API_SECRET
    TWITTER_ACCESS_TOKEN
    TWITTER_ACCESS_TOKEN_SECRET
    TWITTER_BEARER_TOKEN
"""

import json
import os
import sys
from pathlib import Path

# Load .env if present
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

TWITTER_API_KEY = os.environ.get("TWITTER_API_KEY", "")
TWITTER_API_SECRET = os.environ.get("TWITTER_API_SECRET", "")
TWITTER_ACCESS_TOKEN = os.environ.get("TWITTER_ACCESS_TOKEN", "")
TWITTER_ACCESS_TOKEN_SECRET = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET", "")
TWITTER_BEARER_TOKEN = os.environ.get("TWITTER_BEARER_TOKEN", "")

_NOT_CONFIGURED_MSG = (
    "Twitter credentials not configured. "
    "Set TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, "
    "TWITTER_ACCESS_TOKEN_SECRET, and TWITTER_BEARER_TOKEN in your .env file. "
    "Get credentials at: https://developer.twitter.com/en/portal/dashboard"
)


def _credentials_present() -> bool:
    return bool(TWITTER_API_KEY and TWITTER_API_SECRET and
                TWITTER_ACCESS_TOKEN and TWITTER_ACCESS_TOKEN_SECRET)


def _bearer_present() -> bool:
    return bool(TWITTER_BEARER_TOKEN)


# ── Tweepy-based implementation ───────────────────────────────────────────────

def _get_tweepy_client():
    """Return a tweepy.Client instance or raise ImportError/ValueError."""
    try:
        import tweepy  # type: ignore
    except ImportError:
        raise ImportError("tweepy not installed. Run: pip install tweepy")

    if not _credentials_present():
        raise ValueError(_NOT_CONFIGURED_MSG)

    return tweepy.Client(
        bearer_token=TWITTER_BEARER_TOKEN or None,
        consumer_key=TWITTER_API_KEY,
        consumer_secret=TWITTER_API_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_TOKEN_SECRET,
        wait_on_rate_limit=True,
    )


# ── Tool implementations ──────────────────────────────────────────────────────

def tweet_post(text: str) -> str:
    """Post a tweet. Text max 280 chars."""
    if not _credentials_present():
        return f"ERROR: {_NOT_CONFIGURED_MSG}"

    if len(text) > 280:
        return f"ERROR: Tweet text too long ({len(text)} chars). Twitter limit is 280."

    try:
        client = _get_tweepy_client()
        response = client.create_tweet(text=text)
        tweet_id = response.data["id"] if response.data else "unknown"
        return (
            f"Tweet posted successfully!\n"
            f"  Tweet ID: {tweet_id}\n"
            f"  Text: {text}\n"
            f"  URL: https://twitter.com/i/web/status/{tweet_id}"
        )
    except ImportError as e:
        return _post_via_requests(text)
    except Exception as e:
        return f"ERROR posting tweet: {e}"


def _post_via_requests(text: str) -> str:
    """Fallback: post tweet via direct OAuth 1.0a requests (no tweepy)."""
    if not _credentials_present():
        return f"ERROR: {_NOT_CONFIGURED_MSG}"

    try:
        import urllib.request
        import urllib.parse
        import hmac
        import hashlib
        import base64
        import time
        import uuid

        url = "https://api.twitter.com/2/tweets"
        method = "POST"
        nonce = uuid.uuid4().hex
        timestamp = str(int(time.time()))

        # Build OAuth params
        oauth_params = {
            "oauth_consumer_key": TWITTER_API_KEY,
            "oauth_nonce": nonce,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": timestamp,
            "oauth_token": TWITTER_ACCESS_TOKEN,
            "oauth_version": "1.0",
        }

        # Signature base string (POST params not included for JSON body)
        param_str = "&".join(
            f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(v, safe='')}"
            for k, v in sorted(oauth_params.items())
        )
        base_str = "&".join([
            method,
            urllib.parse.quote(url, safe=""),
            urllib.parse.quote(param_str, safe=""),
        ])

        signing_key = (
            urllib.parse.quote(TWITTER_API_SECRET, safe="") + "&" +
            urllib.parse.quote(TWITTER_ACCESS_TOKEN_SECRET, safe="")
        )
        signature = base64.b64encode(
            hmac.new(signing_key.encode(), base_str.encode(), hashlib.sha1).digest()
        ).decode()

        oauth_params["oauth_signature"] = signature
        auth_header = "OAuth " + ", ".join(
            f'{urllib.parse.quote(k, safe="")}="{urllib.parse.quote(v, safe="")}"'
            for k, v in sorted(oauth_params.items())
        )

        body = json.dumps({"text": text}).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Authorization", auth_header)
        req.add_header("Content-Type", "application/json")

        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            tweet_id = result.get("data", {}).get("id", "unknown")
            return (
                f"Tweet posted successfully!\n"
                f"  Tweet ID: {tweet_id}\n"
                f"  Text: {text}\n"
                f"  URL: https://twitter.com/i/web/status/{tweet_id}"
            )
    except Exception as e:
        return f"ERROR posting tweet: {e}"


def tweet_get_timeline(count: int = 10) -> str:
    """Get recent tweets from the authenticated user's home timeline."""
    if not _credentials_present():
        return f"ERROR: {_NOT_CONFIGURED_MSG}"

    try:
        client = _get_tweepy_client()
        # Get own user id first
        me = client.get_me()
        if not me.data:
            return "ERROR: Could not retrieve authenticated user."
        user_id = me.data.id

        response = client.get_users_tweets(
            id=user_id,
            max_results=min(int(count), 100),
            tweet_fields=["created_at", "public_metrics", "text"],
        )
        tweets = response.data or []
        if not tweets:
            return "No tweets found on timeline."

        lines = [f"Last {len(tweets)} tweets:\n"]
        for t in tweets:
            metrics = getattr(t, "public_metrics", {}) or {}
            lines.append(
                f"  [{t.created_at}] ID:{t.id}\n"
                f"    {t.text[:120]}{'...' if len(t.text) > 120 else ''}\n"
                f"    Likes:{metrics.get('like_count',0)} | "
                f"Retweets:{metrics.get('retweet_count',0)} | "
                f"Replies:{metrics.get('reply_count',0)}"
            )
        return "\n".join(lines)

    except ImportError:
        return f"ERROR: tweepy not installed. Run: pip install tweepy"
    except Exception as e:
        return f"ERROR fetching timeline: {e}"


def tweet_search(query: str, count: int = 10) -> str:
    """Search recent tweets by query string."""
    if not _bearer_present() and not _credentials_present():
        return f"ERROR: {_NOT_CONFIGURED_MSG}"

    try:
        client = _get_tweepy_client()
        response = client.search_recent_tweets(
            query=query,
            max_results=min(int(count), 100),
            tweet_fields=["created_at", "public_metrics", "author_id", "text"],
        )
        tweets = response.data or []
        if not tweets:
            return f"No tweets found for query: '{query}'"

        lines = [f"Search results for '{query}' ({len(tweets)} tweets):\n"]
        for t in tweets:
            metrics = getattr(t, "public_metrics", {}) or {}
            lines.append(
                f"  [{t.created_at}] ID:{t.id} AuthorID:{t.author_id}\n"
                f"    {t.text[:120]}{'...' if len(t.text) > 120 else ''}\n"
                f"    Likes:{metrics.get('like_count',0)} | "
                f"Retweets:{metrics.get('retweet_count',0)}"
            )
        return "\n".join(lines)

    except ImportError:
        return f"ERROR: tweepy not installed. Run: pip install tweepy"
    except Exception as e:
        return f"ERROR searching tweets: {e}"


# ── MCP stdio server ──────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "tweet_post",
        "description": "Post a tweet to Twitter/X. Text must be 280 characters or fewer.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Tweet text (max 280 chars)"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "tweet_get_timeline",
        "description": "Get recent tweets from the authenticated user's timeline.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "description": "Number of tweets to fetch (default 10)", "default": 10},
            },
        },
    },
    {
        "name": "tweet_search",
        "description": "Search recent tweets matching a query string.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "count": {"type": "integer", "description": "Max results (default 10)", "default": 10},
            },
            "required": ["query"],
        },
    },
]

TOOL_MAP = {
    "tweet_post": lambda a: tweet_post(a["text"]),
    "tweet_get_timeline": lambda a: tweet_get_timeline(a.get("count", 10)),
    "tweet_search": lambda a: tweet_search(a["query"], a.get("count", 10)),
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
                "serverInfo": {"name": "twitter", "version": "1.0.0"},
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
            sys.stderr.write(f"[twitter_mcp error] {e}\n")
            sys.stderr.flush()


if __name__ == "__main__":
    main()
