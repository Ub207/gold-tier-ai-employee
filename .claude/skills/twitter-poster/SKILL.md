# Skill: twitter-poster

Post to Twitter/X from the AI Employee. All posts require human approval — never auto-tweets.

## Trigger
- `/twitter-poster` — draft a new tweet and route for approval
- `/twitter-poster post [filename]` — post an approved tweet via MCP
- `/twitter-poster timeline` — read the recent timeline
- `/twitter-poster search [query]` — search tweets for a keyword

---

## Hard Rules (Never Break)
- NEVER auto-post. Draft → Pending_Approval → Approved → human confirms → post.
- Max 280 characters per tweet.
- No political content, no harassment, no spam.
- Approval required: always (per Company Handbook).

---

## Step 1 — Read Context

Read before drafting:
- `silver_tier/Business_Goals.md` — pillars, tone, target audience
- `silver_tier/Company_Handbook.md` — tone of voice rules
- Recent tweets from timeline (use `mcp__twitter__tweet_get_timeline`)

---

## Step 2 — Draft Tweet

Write ONE tweet:

| Element | Rule |
|---------|------|
| Length | Max 280 characters |
| Hook | Lead with the value — curiosity, insight, or bold statement |
| Hashtags | Max 2 relevant hashtags at the end |
| Tone | Direct, no hype, no filler words |
| CTA | Optional — "Thoughts?" / "RT if useful" |

DO NOT fabricate results, name-drop clients without permission, or use misleading stats.

---

## Step 3 — Save Draft

Write to `silver_tier/Plans/TW_[YYYYMMDD_HHMM]_[slug].md`:

```markdown
---
type: twitter_post
created: [YYYY-MM-DD HH:MM:SS]
status: draft
characters: [N]
---

[tweet text here — plain, exactly as it will appear on Twitter/X]

---

## Approval Checklist
- [ ] Under 280 characters ([N]/280)
- [ ] Value-first, not promotional spam
- [ ] No misleading claims
- [ ] Approved to post

## To Post
1. Move this file to `silver_tier/Approved/`
2. Run: `/twitter-poster post [filename]`
```

---

## Step 4 — Route to Pending_Approval

Copy file to `silver_tier/Pending_Approval/` with `status: awaiting_approval`.

Print:
```
=== Twitter Draft Ready ===
Draft:   silver_tier/Plans/[filename]
Pending: silver_tier/Pending_Approval/[filename]
Chars:   [N]/280

Next steps:
  1. Review in Obsidian (Pending_Approval/)
  2. Move to Approved/ if happy
  3. Run: /twitter-poster post [filename]
===========================
```

---

## Step 5 — Posting (after human approval)

Human has moved file to `Approved/`. Call:
```
mcp__twitter__tweet_post(text="[tweet text]")
```

On success:
- Log to `silver_tier/Logs/YYYY-MM-DD.json` via `audit_logger.py`
- Move file: `Approved/` → `Done/`
- Print confirmation with tweet URL

---

## Step 6 — Timeline & Search

**Timeline:**
```
mcp__twitter__tweet_get_timeline()
```
Summarize last 5 tweets — topics, engagement, tone notes.

**Search:**
```
mcp__twitter__tweet_search(query="[keyword]")
```
Summarize findings. Suggest content angles based on what's trending.

---

## Required Env Vars
```
TWITTER_API_KEY=
TWITTER_API_SECRET=
TWITTER_ACCESS_TOKEN=
TWITTER_ACCESS_TOKEN_SECRET=
```
