# Skill: social-summary

Pull a cross-platform social media performance summary across Twitter/X, Facebook, and Instagram. Read-only — no posts.

## Trigger
- `/social-summary` — full summary across all platforms
- `/social-summary twitter` — Twitter/X only
- `/social-summary facebook` — Facebook Page only
- `/social-summary instagram` — Instagram only

---

## Hard Rules
- Auto-approved (read-only, no posting).
- Log summary generation to audit trail.

---

## Step 1 — Pull Data from All Platforms

Run all three in sequence:

**Twitter/X:**
```
mcp__twitter__tweet_get_timeline()
```

**Facebook:**
```
mcp__facebook-instagram__facebook_get_page_posts()
```

**Instagram:**
```
mcp__facebook-instagram__instagram_get_posts()
```

Or use the combined summary:
```
mcp__facebook-instagram__get_social_summary()
```

---

## Step 2 — Analyse & Summarise

For each platform, extract:
- Last 5 posts (date, content snippet, engagement)
- Top performing post this week
- Posting cadence (how many posts per week)
- Tone consistency check (matches Business_Goals.md tone?)

---

## Step 3 — Output Report

Write to `silver_tier/Plans/SOCIAL_SUMMARY_[YYYYMMDD_HHMM].md`:

```markdown
---
type: social_summary
generated: [YYYY-MM-DD HH:MM:SS]
platforms: twitter, facebook, instagram
---

# Social Media Summary — [Date]

## Twitter/X
- Posts this week: [N]
- Top tweet: "[snippet]" — [engagement]
- Cadence: [X posts/week]
- Notes: [tone/content observations]

## Facebook Page
- Posts this week: [N]
- Top post: "[snippet]" — [engagement]
- Cadence: [X posts/week]
- Notes: [tone/content observations]

## Instagram
- Posts this week: [N]
- Top post: "[snippet]" — [engagement]
- Cadence: [X posts/week]
- Notes: [image quality/caption notes]

## Cross-Platform Insights
- Best performing content type: [type]
- Content gaps: [what's missing]
- Suggested next posts: [3 ideas aligned with Business_Goals.md]

## LinkedIn (manual check)
Check `silver_tier/LinkedIn_Drafts/` and `silver_tier/Done/` for this week's LI posts.
```

---

## Step 4 — Log

```python
logger.log_action("social_summary", "all_platforms", {"platforms": ["twitter", "facebook", "instagram"]}, "not_required", "n/a", "success")
```

Print:
```
=== Social Summary Generated ===
Platforms: Twitter, Facebook, Instagram
File: silver_tier/Plans/[filename]
================================
```

---

## Required Env Vars
```
TWITTER_API_KEY=
TWITTER_API_SECRET=
TWITTER_ACCESS_TOKEN=
TWITTER_ACCESS_TOKEN_SECRET=
FACEBOOK_ACCESS_TOKEN=
FACEBOOK_PAGE_ID=
INSTAGRAM_USER_ID=
```
