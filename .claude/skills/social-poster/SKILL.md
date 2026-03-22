# Skill: social-poster

Post to Facebook and/or Instagram. All posts require human approval — never auto-posts.

## Trigger
- `/social-poster` — draft a new post for Facebook and/or Instagram
- `/social-poster facebook [filename]` — post approved content to Facebook Page
- `/social-poster instagram [filename]` — post approved image to Instagram
- `/social-poster summary` — get recent post performance summary

---

## Hard Rules (Never Break)
- NEVER auto-post. Draft → Pending_Approval → Approved → human confirms → post.
- Instagram requires an image URL. If no image is provided, post to Facebook only.
- Approval required: always (per Company Handbook).
- Log every post action to audit trail.

---

## Step 1 — Read Context

Read before drafting:
- `silver_tier/Business_Goals.md` — pillars, tone, target audience
- `silver_tier/Company_Handbook.md` — social media rules
- Use `mcp__facebook-instagram__get_social_summary` to check recent posts

---

## Step 2 — Choose Platform(s)

Ask or infer:
- **Facebook only** — text posts, links, longer-form content
- **Instagram only** — image-first, visual content (requires image URL)
- **Both** — adapted versions for each platform

---

## Step 3 — Draft Post

### Facebook post rules:
| Element | Rule |
|---------|------|
| Length | 100–500 characters ideal; max 63,206 |
| Hook | Bold opening line |
| Body | Value-first, 2–4 short paragraphs |
| CTA | Ask a question, share link, or tag relevant page |
| Hashtags | Max 5 |

### Instagram caption rules:
| Element | Rule |
|---------|------|
| Length | 125 characters before "more" cutoff; max 2,200 |
| Hook | First line must grab attention |
| Hashtags | 5–15, placed at end or in comment |
| Image | Required — provide URL or note "add image" |

---

## Step 4 — Save Draft

Write to `silver_tier/Plans/SOCIAL_[FB|IG|BOTH]_[YYYYMMDD_HHMM]_[slug].md`:

```markdown
---
type: social_post
platforms: [facebook | instagram | both]
created: [YYYY-MM-DD HH:MM:SS]
status: draft
image_url: [URL or leave blank]
---

## Facebook Post
[facebook caption here]

---

## Instagram Caption
[instagram caption here]

Image: [URL or "INSERT IMAGE URL"]

---

## Approval Checklist
- [ ] Value-first content (not pure promotion)
- [ ] Hashtags within limits
- [ ] Image URL provided (Instagram)
- [ ] Approved to post

## To Post
1. Move this file to `silver_tier/Approved/`
2. Run: `/social-poster facebook [filename]` or `/social-poster instagram [filename]`
```

---

## Step 5 — Route to Pending_Approval

Copy file to `silver_tier/Pending_Approval/`. Print confirmation.

---

## Step 6 — Posting (after human approval)

**Facebook:**
```
mcp__facebook-instagram__facebook_post(message="[text]")
```

**Instagram (requires image):**
```
mcp__facebook-instagram__instagram_post_image(image_url="[url]", caption="[text]")
```

On success:
- Log to `silver_tier/Logs/YYYY-MM-DD.json`
- Move file: `Approved/` → `Done/`

---

## Step 7 — Social Summary

Call:
```
mcp__facebook-instagram__get_social_summary()
```

Summarize:
- Recent Facebook page posts (last 5)
- Recent Instagram posts (last 5)
- Engagement trends
- Content angle suggestions

---

## Required Env Vars
```
FACEBOOK_ACCESS_TOKEN=
FACEBOOK_PAGE_ID=
INSTAGRAM_USER_ID=
```
