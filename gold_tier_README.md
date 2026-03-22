# Gold Tier AI Employee — Architecture & Setup Guide

## Overview

Gold Tier extends the Silver Tier AI Employee with enterprise-grade features:
- Multi-platform social media (Twitter, Facebook, Instagram)
- Accounting integration (Odoo ERP)
- Comprehensive audit logging
- Weekly CEO briefings
- Process health monitoring (watchdog)
- Robust error handling with retry logic
- Stop hook to prevent premature task exit

---

## System Architecture

```
D:/gold_tier/
├── silver_tier/                  # Obsidian vault (data store)
│   ├── Needs_Action/             # Incoming tasks (emails, WhatsApp, etc.)
│   ├── Done/                     # Completed tasks
│   ├── Approved/                 # Human-approved actions
│   ├── Rejected/                 # Rejected actions
│   ├── Pending_Approval/         # Awaiting human review
│   ├── Plans/                    # AI-generated action plans
│   ├── In_Progress/              # Tasks currently being worked on [GOLD]
│   ├── LinkedIn_Drafts/          # LinkedIn post drafts
│   ├── Logs/                     # Audit logs YYYY-MM-DD.json [GOLD]
│   ├── Invoices/                 # Invoice records [GOLD]
│   ├── Accounting/               # Financial data [GOLD]
│   └── Briefings/                # CEO briefing files [GOLD]
│
├── Core Watchers
│   ├── gmail_oauth_watcher.py    # Monitors Gmail inbox
│   └── whatsapp_watcher.py       # Monitors WhatsApp (Playwright)
│
├── MCP Servers (Claude Code tools)
│   ├── linkedin_personal_mcp.py  # LinkedIn personal account
│   ├── linkedin_company_mcp.py   # LinkedIn company page
│   ├── email_mcp.py              # Email sending (SMTP)
│   ├── twitter_mcp.py            # Twitter/X API [GOLD]
│   ├── facebook_instagram_mcp.py # Facebook + Instagram [GOLD]
│   └── odoo_mcp.py               # Odoo ERP accounting [GOLD]
│
├── Processing Pipeline
│   ├── inbox_planner.py          # Turns inbox items into plans
│   ├── auto_approver.py          # Auto-approves low-risk actions
│   ├── approval_executor.py      # Executes approved actions
│   └── workflow_runner.py        # Main orchestration loop
│
├── Gold Tier Components
│   ├── audit_logger.py           # Comprehensive JSON audit logging [GOLD]
│   ├── watchdog.py               # Process health monitor + auto-restart [GOLD]
│   ├── error_handler.py          # Retry with exponential backoff [GOLD]
│   ├── ceo_briefing_generator.py # Weekly CEO briefing generator [GOLD]
│   └── gold_tier_orchestrator.py # Master orchestrator [GOLD]
│
├── Launchers
│   ├── run_all.py                # Silver + Gold process launcher
│   └── gold_tier_orchestrator.py # Gold Tier master orchestrator
│
├── Config
│   ├── .mcp.json                 # MCP server definitions (10 servers)
│   ├── .env                      # Environment variables (secrets)
│   ├── .env.example              # Template for .env
│   └── .claude/
│       ├── settings.local.json   # Claude Code permissions + stop hook
│       ├── hooks/stop.py         # Ralph Wiggum stop hook [GOLD]
│       └── skills/               # Agent skill definitions
```

---

## Gold Tier Components

### 1. `audit_logger.py` — Audit Logging
Every system action is logged to `silver_tier/Logs/YYYY-MM-DD.json` as JSON lines.

```python
from audit_logger import AuditLogger
logger = AuditLogger()
logger.log_action("email_send", "client@example.com",
                  parameters={"subject": "Invoice"},
                  approval_status="approved", approved_by="human",
                  result="success")

# Get summary
summary = logger.generate_summary(days=7)
```

### 2. `odoo_mcp.py` — Odoo ERP Integration
Connects to Odoo Community Edition via JSON-RPC API.

Tools available in Claude Code:
- `odoo_create_invoice` — Create DRAFT invoices (never auto-posts)
- `odoo_list_invoices` — List invoices by state
- `odoo_get_partner` — Search for customers
- `odoo_list_payments` — List recent payments
- `odoo_get_revenue_summary` — Revenue analytics

### 3. `twitter_mcp.py` — Twitter/X Integration
Uses Tweepy (Twitter API v2) for posting and searching.

Tools: `tweet_post`, `tweet_get_timeline`, `tweet_search`

### 4. `facebook_instagram_mcp.py` — Social Media
Uses Facebook Graph API for both Facebook Pages and Instagram Business.

Tools: `facebook_post`, `facebook_get_page_posts`, `instagram_post_image`, `instagram_get_posts`, `get_social_summary`

### 5. `ceo_briefing_generator.py` — Weekly Briefing
Generates comprehensive Monday morning briefings from vault data.

```bash
python ceo_briefing_generator.py            # generate now
python ceo_briefing_generator.py --schedule # register Task Scheduler job
python ceo_briefing_generator.py --stdout   # print to terminal
```

Output: `silver_tier/Briefings/YYYY-MM-DD_Monday_Briefing.md`

### 6. `watchdog.py` — Process Monitor
Monitors Gmail and WhatsApp watchers and auto-restarts them if they crash.

```bash
python watchdog.py              # continuous monitoring (60s interval)
python watchdog.py --check      # single check and exit
python watchdog.py --status     # print status table
```

Creates alert files in `silver_tier/Needs_Action/ALERT_system_down_*.md` after 3 failed restarts.

### 7. `error_handler.py` — Retry Logic
```python
from error_handler import retry_with_backoff, classify_error

@retry_with_backoff(max_retries=3, initial_delay=1.0, backoff_factor=2.0)
def call_external_api():
    ...

# Or classify errors manually
error_type = classify_error(exception)  # "transient" or "permanent"
```

### 8. `.claude/hooks/stop.py` — Ralph Wiggum Stop Hook
Intercepts Claude Code's exit to check for unfinished tasks in `Needs_Action/`.
If pending items exist, Claude is told to continue working.

---

## Setup Instructions

### 1. Copy and configure environment variables
```bash
cp .env.example .env
```

Edit `.env` with your credentials:

| Variable | Required For | Where to Get |
|----------|-------------|--------------|
| `ANTHROPIC_API_KEY` | AI reasoning | console.anthropic.com |
| `EMAIL_ADDRESS` | Gmail watcher | your Gmail address |
| `EMAIL_APP_PASSWORD` | Gmail watcher | myaccount.google.com/apppasswords |
| `ODOO_URL` | Odoo MCP | Your Odoo instance URL |
| `ODOO_DB` | Odoo MCP | Your Odoo database name |
| `ODOO_USERNAME` | Odoo MCP | Odoo admin username |
| `ODOO_PASSWORD` | Odoo MCP | Odoo admin password |
| `TWITTER_API_KEY` | Twitter MCP | developer.twitter.com |
| `TWITTER_API_SECRET` | Twitter MCP | developer.twitter.com |
| `TWITTER_ACCESS_TOKEN` | Twitter MCP | developer.twitter.com |
| `TWITTER_ACCESS_TOKEN_SECRET` | Twitter MCP | developer.twitter.com |
| `TWITTER_BEARER_TOKEN` | Twitter MCP | developer.twitter.com |
| `FACEBOOK_ACCESS_TOKEN` | Facebook/IG MCP | developers.facebook.com |
| `FACEBOOK_PAGE_ID` | Facebook MCP | Facebook Page settings |
| `INSTAGRAM_USER_ID` | Instagram MCP | Facebook Graph API Explorer |
| `LINKEDIN_COMPANY_SLUG` | LinkedIn company | LinkedIn URL slug |

### 2. Install Python dependencies
```bash
pip install anthropic playwright requests tweepy
playwright install chromium
```

### 3. Start the system

**Option A: Gold Tier Orchestrator (recommended)**
```bash
python gold_tier_orchestrator.py
```

**Option B: Original launcher (updated for Gold Tier)**
```bash
python run_all.py
```

**Option C: Single workflow run**
```bash
python run_all.py --once
```

### 4. Register CEO Briefing (Windows Task Scheduler)
```bash
python run_all.py --register-briefing
# or
python ceo_briefing_generator.py --schedule
```

### 5. Add MCP servers to Claude Code
The `.mcp.json` file is pre-configured. Claude Code will automatically load all 10 MCP servers when you open this project.

Enabled servers:
- `linkedin` — Personal LinkedIn posting
- `linkedin-company` — Company LinkedIn posting
- `email` — SMTP email sending
- `twitter` — Twitter/X integration
- `facebook-instagram` — Facebook + Instagram
- `odoo` — Odoo ERP accounting
- `filesystem` — Vault file operations
- `browser` — Web automation (Playwright)
- `calendar` — Google Calendar integration
- `slack` — Slack messaging

### 6. Agent Skills

All AI functionality is exposed as Claude Agent Skills (`/skill-name`):

| Skill | Command | Purpose |
|-------|---------|---------|
| `/wa-message-processor` | Auto | WA message → plan → draft → approval |
| `/plan-generator` | Manual | Create structured PLAN_*.md |
| `/reply-drafter` | Manual | Generate 3-4 reply options |
| `/approval-checker` | Manual | Check Pending_Approval, trigger send |
| `/approval-handler` | Manual | Move to Approved or Rejected |
| `/whatsapp-sender-mcp` | Manual | Pre-fill WhatsApp Web reply |
| `/linkedin-personal-poster` | Manual | Personal LinkedIn post workflow |
| `/linkedin-company-poster` | Manual | Company LinkedIn post workflow |
| `/gmail-send` | Manual | Send email via Gmail SMTP |
| `/human-approval` | Manual | Request human approval for action |
| `/vault-file-manager` | Manual | Create/move/read vault files |
| `/twitter-poster` | Manual | Tweet → approval → post [GOLD] |
| `/social-poster` | Manual | Facebook/Instagram post workflow [GOLD] |
| `/social-summary` | Manual | Cross-platform social media summary [GOLD] |
| `/odoo-invoice` | Manual | Create draft invoice in Odoo ERP [GOLD] |
| `/ceo-briefing` | Manual | Generate weekly CEO briefing [GOLD] |

---

## How to Run

### Full system startup
```bash
python gold_tier_orchestrator.py
```

### Check system health
```bash
python gold_tier_orchestrator.py --status
python watchdog.py --status
```

### Generate CEO briefing manually
```bash
python ceo_briefing_generator.py
```

### View audit logs
```bash
python audit_logger.py --summary
```

### Test without making changes
```bash
python gold_tier_orchestrator.py --test
```

---

## Vault Workflow

```
Email/WhatsApp arrives
        ↓
  Needs_Action/ (new .md file created)
        ↓
  inbox_planner.py → Plans/ (action plan)
        ↓
  auto_approver.py → either:
    - Approved/ (low risk, auto-approved)
    - Pending_Approval/ (requires human review)
        ↓
  approval_executor.py → executes approved actions
        ↓
  Done/ (task complete, audit log entry written)
```

---

## Security Notes

1. **Never commit `.env`** — it contains your API keys and passwords. It is in `.gitignore`.
2. **Odoo creates DRAFT only** — `odoo_mcp.py` never auto-posts invoices. All financial writes require human confirmation.
3. **WhatsApp session data** is stored locally at `silver_tier/whatsapp_session/`. Do not share.
4. **LinkedIn session data** is stored locally at `silver_tier/linkedin_session/`. Do not share.
5. **API keys rotation** — Rotate all API keys if this directory is ever accidentally exposed.
6. **Auto-approver scope** — `auto_approver.py` is configured for low-risk actions only. Review its risk thresholds before production use.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| WhatsApp watcher not connecting | Run `python whatsapp_watcher.py --setup` to re-authenticate |
| Gmail watcher not starting | Check `EMAIL_ADDRESS` and `EMAIL_APP_PASSWORD` in `.env` |
| Odoo connection refused | Verify `ODOO_URL` is correct and Odoo is running |
| Twitter API errors | Check API v2 access tier — free tier has rate limits |
| Facebook/Instagram errors | Ensure your Page Access Token has `pages_manage_posts` permission |
| CEO briefing empty | Add data to `silver_tier/Accounting/Current_Month.md` |
| Watchdog alert files | Check `logs/{process_name}.log` for error details |

---

*Personal AI Employee — Gold Tier | Built for the Personal AI Employee Hackathon*
