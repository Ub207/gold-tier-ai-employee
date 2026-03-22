# Personal AI Employee — Gold Tier
*Claude Code project context. Read this before every session.*

## What This Project Is
A Digital FTE (Full-Time Equivalent) — an AI agent that proactively manages personal and business affairs 24/7.
**Stack:** Claude Code (brain) + Obsidian vault (memory/GUI) + Python watchers (senses) + MCP servers (hands)

---

## Vault Location
**All vault files live at:** `D:/gold_tier/silver_tier/`

```
silver_tier/
├── Dashboard.md              ← real-time system status
├── Company_Handbook.md       ← rules of engagement (READ THIS FIRST)
├── Business_Goals.md         ← Q1 targets and KPIs
├── Needs_Action/             ← watcher output (EMAIL_*, WA_*, FILE_*)
├── Plans/                    ← PLAN_*.md created before every action
├── Pending_Approval/         ← awaiting human decision
├── Approved/                 ← approved → execute
├── Rejected/                 ← rejected with reason
├── Done/                     ← completed and archived
├── LinkedIn_Drafts/          ← LI_*.md drafts
├── Logs/                     ← YYYY-MM-DD.json audit trail
├── Briefings/                ← Monday morning CEO briefings
├── Invoices/                 ← generated invoices
├── Accounting/               ← bank transactions, Current_Month.md
└── In_Progress/              ← actively being worked on
```

---

## Golden Rules (Never Break)
1. **Plan first.** Every action needs a `PLAN_*.md` in `/Plans` before execution.
2. **Human approves.** Sensitive actions go to `/Pending_Approval` — never auto-execute.
3. **Draft only.** All Odoo accounting entries are DRAFT — never auto-post.
4. **Never auto-send.** LinkedIn, WhatsApp, email — human always clicks Send/Post.
5. **Log everything.** Use `audit_logger.py` for every action taken.
6. **Check rate limits.** Max 2 LinkedIn posts/week per profile. Max 10 emails/hour.

### Approval Required For:
| Action | Threshold |
|--------|-----------|
| WhatsApp reply | Always |
| Email reply to client | Always |
| LinkedIn post | Always |
| Payment / invoice action | Always (>PKR 10,000 = secondary approval) |
| New contact outreach | Always |
| Social media posts (FB/IG/Twitter) | Always |

### Auto-Approved (no human needed):
- Creating/editing vault files
- Generating drafts
- Updating Dashboard.md
- Reading emails/messages (no action taken)
- Logging to audit trail

---

## Key Scripts

| Script | Purpose | Run |
|--------|---------|-----|
| `run_all.py` | Start all Silver+Gold processes | `python run_all.py` |
| `gold_tier_orchestrator.py` | Master Gold orchestrator | `python gold_tier_orchestrator.py` |
| `workflow_runner.py` | Main processing loop (every 5 min) | auto via run_all |
| `gmail_oauth_watcher.py` | Gmail monitoring | auto via run_all |
| `whatsapp_watcher.py` | WhatsApp Web monitoring | auto via run_all |
| `inbox_planner.py` | Process Needs_Action → Plans | auto via workflow |
| `approval_executor.py` | Execute Approved/ items | auto via run_all |
| `ceo_briefing_generator.py` | Monday morning briefing | `python ceo_briefing_generator.py` |
| `watchdog.py` | Monitor & restart crashed processes | auto via run_all |
| `audit_logger.py` | JSON audit logging | imported by other scripts |
| `error_handler.py` | Retry with exponential backoff | imported by other scripts |

---

## MCP Servers (`.mcp.json`) — 10 total

| Server | Script | Tools |
|--------|--------|-------|
| `linkedin` | `linkedin_personal_mcp.py` | Personal LinkedIn posts, check limit |
| `linkedin-company` | `linkedin_company_mcp.py` | Company page posts, image support |
| `email` | `email_mcp.py` | send_email, read_emails, search_emails, mark_read, create_draft |
| `twitter` | `twitter_mcp.py` | tweet_post, get_timeline, search |
| `facebook-instagram` | `facebook_instagram_mcp.py` | fb_post, ig_post, get_posts, social_summary |
| `odoo` | `odoo_mcp.py` | create_invoice, list_invoices, list_payments, revenue_summary (draft-only) |
| `filesystem` | `filesystem_mcp.py` | read_file, write_file, list_folder, move_file, create_action_file, search_vault |
| `browser` | `browser_mcp.py` | navigate, screenshot, click, fill_form, get_text, close |
| `calendar` | `calendar_mcp.py` | list_events, create_event, update_event, delete_event, find_free_slots |
| `slack` | `slack_mcp.py` | send_message, get_messages, list_channels, upload_file, set_status, search |

---

## Agent Skills (`/skill-name`)

| Skill | Trigger | What it does |
|-------|---------|-------------|
| `/wa-message-processor` | WA_*.md in Needs_Action | Analyze → Plan → Draft → Route to approval |
| `/plan-generator` | Any task | Creates structured PLAN_*.md |
| `/reply-drafter` | Message file | Generates 3–4 reply options |
| `/approval-checker` | Check Pending_Approval | Triggers send flow, moves to Done |
| `/whatsapp-sender-mcp` | Approved WA file | Pre-fills WhatsApp Web reply |
| `/linkedin-personal-poster` | — | Personal post: draft → approval → composer |
| `/linkedin-company-poster` | — | Company post: draft → approval → composer |
| `/approval-handler` | Pending item | Move to Approved or Rejected |
| `/vault-file-manager` | — | Create/move/read vault files |
| `/gmail-send` | — | Send email via Gmail |
| `/human-approval` | — | Request human approval for action |
| `/twitter-poster` | — | Tweet: draft → approval → post via MCP [GOLD] |
| `/social-poster` | — | Facebook/Instagram: draft → approval → post [GOLD] |
| `/social-summary` | — | Pull cross-platform social media summary [GOLD] |
| `/odoo-invoice` | — | Create draft invoice in Odoo ERP [GOLD] |
| `/ceo-briefing` | — | Generate weekly CEO briefing from vault data [GOLD] |

---

## Gold Tier Additions (built 2026-03-11)

### Audit Logging
Every action must be logged:
```python
from audit_logger import AuditLogger
logger = AuditLogger("silver_tier")
logger.log_action("email_send", "client@example.com", {"subject": "..."}, "approved", "human", "success")
```

### Error Handling
Use retry for external API calls:
```python
from error_handler import retry_with_backoff, classify_error
result = retry_with_backoff(api_call, max_retries=3)
```

### CEO Briefing
Auto-generated every Monday 7AM from vault data:
- Reads: Business_Goals.md, Accounting/Current_Month.md, Done/, Logs/
- Outputs: `Briefings/YYYY-MM-DD_Monday_Briefing.md`

### Ralph Wiggum Stop Hook
`.claude/hooks/stop.py` — prevents Claude from stopping if Needs_Action/ still has unprocessed files.

---

## Environment Variables (`.env`)
```
# Email
GMAIL_ADDRESS=
GMAIL_APP_PASSWORD=

# LinkedIn
LINKEDIN_COMPANY_SLUG=
LINKEDIN_PROFILE_URL=

# Twitter/X
TWITTER_API_KEY=
TWITTER_API_SECRET=
TWITTER_ACCESS_TOKEN=
TWITTER_ACCESS_TOKEN_SECRET=

# Facebook / Instagram
FACEBOOK_ACCESS_TOKEN=
FACEBOOK_PAGE_ID=
INSTAGRAM_USER_ID=

# Odoo (local, http://localhost:8069)
ODOO_URL=http://localhost:8069
ODOO_DB=
ODOO_USERNAME=
ODOO_PASSWORD=

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_USER_TOKEN=xoxp-...
```

---

## Workflow Flow (Full Picture)
```
Watcher detects event
        ↓
Creates EMAIL_*.md / WA_*.md in Needs_Action/
        ↓
workflow_runner.py → inbox_planner.py
        ↓
Creates PLAN_*.md in Plans/
        ↓
Creates approval request in Pending_Approval/
        ↓
Human reviews → moves to Approved/ or Rejected/
        ↓
approval_executor.py executes the action
        ↓
audit_logger.py logs the result
        ↓
File moves to Done/
        ↓
Dashboard.md updated
```

---

## Business Context
- **Target:** AI automation consulting for solo founders and small agencies
- **Currency:** PKR (Pakistan Rupees) — flag any >PKR 10,000 for secondary approval
- **Business hours:** 10am–7pm IST
- **WA response target:** < 2 hours during business hours
- **LinkedIn:** Max 2 posts/week per profile (personal + company = 4 total)
