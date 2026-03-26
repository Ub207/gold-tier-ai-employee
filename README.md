<p align="center">
  <img src="https://img.shields.io/badge/Tier-Gold-FFD700?style=for-the-badge&logo=stackexchange&logoColor=white" alt="Gold Tier" />
  <img src="https://img.shields.io/badge/Status-Production-brightgreen?style=for-the-badge" alt="Production" />
  <img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.9+" />
  <img src="https://img.shields.io/badge/Claude_AI-Powered-6B48FF?style=for-the-badge&logo=anthropic&logoColor=white" alt="Claude AI" />
  <img src="https://img.shields.io/badge/MCP_Servers-10-FF6B35?style=for-the-badge&logo=serverless&logoColor=white" alt="10 MCP Servers" />
</p>

<h1 align="center">AI Employee &mdash; Gold Tier</h1>

<p align="center">
  <strong>Advanced multi-platform automation with CEO briefings, Odoo ERP, and cross-platform social media</strong>
</p>

<p align="center">
  A Digital FTE (Full-Time Equivalent) &mdash; an AI agent that proactively manages personal and business affairs 24/7.<br/>
  Built on <strong>Claude Code</strong> (brain) + <strong>Obsidian vault</strong> (memory/GUI) + <strong>Python watchers</strong> (senses) + <strong>MCP servers</strong> (hands).
</p>

---

## What Gold Tier Adds Over Silver

| Feature | Silver Tier | Gold Tier |
|---------|:-----------:|:---------:|
| Gmail monitoring & reply drafting | Yes | Yes |
| WhatsApp monitoring & reply drafting | Yes | Yes |
| LinkedIn personal posting | Yes | Yes |
| LinkedIn company posting | Yes | Yes |
| Obsidian vault workflow engine | Yes | Yes |
| Human-in-the-loop approvals | Yes | Yes |
| **Twitter/X integration** | &mdash; | Yes |
| **Facebook page management** | &mdash; | Yes |
| **Instagram business posting** | &mdash; | Yes |
| **Slack workspace integration** | &mdash; | Yes |
| **Odoo ERP accounting (13 tools)** | &mdash; | Yes |
| **Google Calendar management** | &mdash; | Yes |
| **CEO weekly briefings** | &mdash; | Yes |
| **Comprehensive audit logging** | &mdash; | Yes |
| **Error handling with retry logic** | &mdash; | Yes |
| **Process watchdog & auto-restart** | &mdash; | Yes |
| **Ralph Wiggum stop hook** | &mdash; | Yes |

---

## Capabilities Matrix

### Communication (4 platforms)
| Platform | Read | Draft | Send | Approval Required |
|----------|:----:|:-----:|:----:|:-----------------:|
| Gmail | Automatic | AI-generated | Via MCP | Yes |
| WhatsApp | Automatic | AI-generated | Pre-filled | Yes |
| Slack | Via MCP | AI-generated | Via MCP | Yes |
| Calendar | Via MCP | AI-generated | Via MCP | Yes |

### Social Media (5 platforms)
| Platform | Post | Schedule | Analytics | Rate Limit |
|----------|:----:|:--------:|:---------:|:----------:|
| LinkedIn Personal | Yes | Yes | &mdash; | 2/week |
| LinkedIn Company | Yes | Yes | &mdash; | 2/week |
| Twitter/X | Yes | &mdash; | Timeline + Search | API tier dependent |
| Facebook Pages | Yes | &mdash; | Post history | &mdash; |
| Instagram Business | Yes (image) | &mdash; | Post history | &mdash; |

### Business Operations
| System | Capabilities | Safety |
|--------|-------------|--------|
| Odoo ERP | Invoices, bills, payments, partners, revenue analytics | Draft-only (never auto-posts) |
| Audit Logging | JSON audit trail, 7-day summaries, action tracking | Automatic for all actions |
| CEO Briefings | Weekly auto-generated from vault data | Monday 7 AM |

---

## Architecture

```
+------------------------------------------------------------------+
|                        GOLD TIER ORCHESTRATOR                     |
|                    gold_tier_orchestrator.py                       |
+--------------+----------------+---------------+-------------------+
|  WATCHERS    |   PIPELINE     |  MCP SERVERS  |  GOLD COMPONENTS  |
+--------------+----------------+---------------+-------------------+
| Gmail OAuth  | inbox_planner  | linkedin      | audit_logger      |
| WhatsApp     | auto_approver  | linkedin-co   | ceo_briefing_gen  |
| Filesystem   | approval_exec  | email         | error_handler     |
|              | workflow_run   | twitter       | process_watchdog  |
|              |                | facebook-ig   | stop hook         |
|              |                | odoo          |                   |
|              |                | filesystem    |                   |
|              |                | browser       |                   |
|              |                | calendar      |                   |
|              |                | slack         |                   |
+--------------+----------------+---------------+-------------------+
                               |
                    +----------v----------+
                    |   OBSIDIAN VAULT    |
                    |   (silver_tier/)    |
                    +---------------------+
                    | Needs_Action/       |
                    | Plans/              |
                    | Pending_Approval/   |
                    | Approved/           |
                    | Done/               |
                    | Logs/               |
                    | Briefings/          |
                    | Invoices/           |
                    | Accounting/         |
                    +---------------------+
```

---

## MCP Server Diagram

Gold Tier connects **10 MCP servers** to Claude Code, giving the AI agent hands to act across platforms:

```
                          +---------------+
                          |  Claude Code  |
                          |   (Brain)     |
                          +-------+-------+
                                  |
              +-------------------+-------------------+
              |                   |                   |
     +--------v--------+  +------v-------+  +--------v--------+
     | COMMUNICATION   |  |   SOCIAL     |  |   BUSINESS      |
     +-----------------+  +--------------+  +-----------------+
     | email_mcp       |  | linkedin     |  | odoo_mcp        |
     | slack_mcp       |  | linkedin-co  |  | calendar_mcp    |
     | browser_mcp     |  | twitter_mcp  |  | filesystem_mcp  |
     |                 |  | fb_ig_mcp    |  |                 |
     +-----------------+  +--------------+  +-----------------+
```

---

## Odoo ERP Integration

The `odoo_mcp.py` server provides **13 tools** for full accounting automation via JSON-RPC:

| Tool | Description | Safety |
|------|-------------|--------|
| `odoo_create_invoice` | Create customer invoices | Draft only |
| `odoo_list_invoices` | List invoices by state/date | Read-only |
| `odoo_post_invoice` | Post a draft invoice | Requires approval |
| `odoo_create_vendor_bill` | Create vendor/supplier bills | Draft only |
| `odoo_create_partner` | Create customer/vendor records | Auto-approved |
| `odoo_get_partner` | Search for partners | Read-only |
| `odoo_create_payment_draft` | Create payment records | Draft only |
| `odoo_confirm_payment` | Confirm a draft payment | Requires approval |
| `odoo_list_payments` | List recent payments | Read-only |
| `odoo_get_overdue_invoices` | Retrieve overdue invoices | Read-only |
| `odoo_create_payment_followup` | Generate payment follow-up actions | Draft only |
| `odoo_get_account_summary` | Account balance summary | Read-only |
| `odoo_get_revenue_summary` | Revenue analytics and reporting | Read-only |

> **Safety rule:** All financial writes create DRAFT entries only. A human must explicitly approve before any invoice is posted or payment is confirmed. Amounts exceeding PKR 10,000 require secondary approval.

---

## Social Media Automation

### 5 Platforms, 1 Workflow

Every social media action follows the same vault-based workflow:

```
AI drafts content -> Plans/*.md -> Pending_Approval/*.md -> Human reviews -> Approved/*.md -> MCP sends
```

**LinkedIn** &mdash; Personal and company page posting with image support. Rate limited to 2 posts/week per profile.

**Twitter/X** &mdash; Post tweets, search trending topics, and pull timeline data. Uses Twitter API v2 via Tweepy.

**Facebook Pages** &mdash; Publish posts to your business page. Retrieve post history and engagement data.

**Instagram Business** &mdash; Publish image posts via Facebook Graph API. Pull post history and insights.

**Slack** &mdash; Send messages, search channels, upload files, and set status. Full workspace integration.

---

## CEO Briefing

Every Monday at 7 AM, the system auto-generates a comprehensive briefing from vault data:

**Data sources:**
- `Business_Goals.md` &mdash; KPI tracking and Q1 targets
- `Accounting/Current_Month.md` &mdash; Financial performance
- `Done/` &mdash; Completed tasks for the week
- `Logs/` &mdash; Audit trail analysis

**Output:** `Briefings/YYYY-MM-DD_Monday_Briefing.md`

```bash
python ceo_briefing_generator.py            # Generate now
python ceo_briefing_generator.py --schedule # Register with Windows Task Scheduler
python ceo_briefing_generator.py --stdout   # Print to terminal
```

---

## Audit Logging & Error Handling

### Audit Logger
Every system action is recorded to `Logs/YYYY-MM-DD.json` as structured JSON:

```python
from audit_logger import AuditLogger

logger = AuditLogger()
logger.log_action(
    action="email_send",
    target="client@example.com",
    parameters={"subject": "Invoice #1042"},
    approval_status="approved",
    approved_by="human",
    result="success"
)

# Weekly summary
summary = logger.generate_summary(days=7)
```

### Error Handler
Resilient external API calls with exponential backoff:

```python
from error_handler import retry_with_backoff, classify_error

@retry_with_backoff(max_retries=3, initial_delay=1.0, backoff_factor=2.0)
def call_external_api():
    ...

error_type = classify_error(exception)  # "transient" or "permanent"
```

### Process Watchdog
Monitors watchers and auto-restarts crashed processes. Creates alert files after 3 failed restarts.

```bash
python process_watchdog.py              # Continuous monitoring (60s interval)
python process_watchdog.py --check      # Single health check
python process_watchdog.py --status     # Status table
```

---

## Vault Workflow

```
  Email / WhatsApp / Event arrives
              |
              v
      +----------------+
      | Needs_Action/  |  <-- Watchers create EMAIL_*.md / WA_*.md
      +-------+--------+
              v
      +----------------+
      |    Plans/      |  <-- inbox_planner.py generates action plan
      +-------+--------+
              v
      +--------------------+
      | Pending_Approval/  |  <-- Human reviews in Obsidian
      +-------+------------+
              v
      +----------------+
      |   Approved/    |  <-- Human moves file (or auto_approver for low-risk)
      +-------+--------+
              v
      +----------------+
      |    Done/       |  <-- approval_executor.py executes + audit log
      +----------------+
```

---

## Agent Skills

All AI functionality is exposed as Claude Agent Skills:

| Skill | Description |
|-------|-------------|
| `/wa-message-processor` | WhatsApp message analysis, planning, and draft generation |
| `/plan-generator` | Create structured PLAN_*.md for any task |
| `/reply-drafter` | Generate 3-4 contextual reply options |
| `/approval-checker` | Check Pending_Approval and trigger send flows |
| `/approval-handler` | Move items to Approved or Rejected |
| `/whatsapp-sender-mcp` | Pre-fill WhatsApp Web reply via browser automation |
| `/linkedin-personal-poster` | End-to-end personal LinkedIn post workflow |
| `/linkedin-company-poster` | End-to-end company LinkedIn post workflow |
| `/gmail-send` | Send email via Gmail SMTP |
| `/human-approval` | Request human approval for sensitive actions |
| `/vault-file-manager` | Create, move, and read vault files |
| `/twitter-poster` | Tweet draft, approval, and posting workflow |
| `/social-poster` | Facebook/Instagram post workflow |
| `/social-summary` | Cross-platform social media analytics summary |
| `/odoo-invoice` | Create draft invoices in Odoo ERP |
| `/ceo-briefing` | Generate weekly CEO briefing from vault data |

---

## Getting Started

### Prerequisites

- Python 3.9+
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI installed
- Obsidian (for vault GUI &mdash; optional but recommended)
- Odoo Community Edition (for ERP features &mdash; optional)

### 1. Clone and configure

```bash
git clone https://github.com/Ub207/gold-tier-ai-employee.git
cd gold-tier-ai-employee
cp .env.example .env
```

Edit `.env` with your credentials:

| Variable | Service | Where to Get |
|----------|---------|--------------|
| `ANTHROPIC_API_KEY` | Claude AI | [console.anthropic.com](https://console.anthropic.com) |
| `EMAIL_ADDRESS` | Gmail | Your Gmail address |
| `EMAIL_APP_PASSWORD` | Gmail | [App Passwords](https://myaccount.google.com/apppasswords) |
| `ODOO_URL`, `ODOO_DB`, `ODOO_USERNAME`, `ODOO_PASSWORD` | Odoo ERP | Your Odoo instance |
| `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_TOKEN_SECRET` | Twitter/X | [developer.twitter.com](https://developer.twitter.com) |
| `FACEBOOK_ACCESS_TOKEN`, `FACEBOOK_PAGE_ID` | Facebook | [developers.facebook.com](https://developers.facebook.com) |
| `INSTAGRAM_USER_ID` | Instagram | Facebook Graph API Explorer |
| `LINKEDIN_COMPANY_SLUG` | LinkedIn | Your company page URL slug |
| `SLACK_BOT_TOKEN`, `SLACK_USER_TOKEN` | Slack | [api.slack.com/apps](https://api.slack.com/apps) |

### 2. Install dependencies

```bash
pip install anthropic playwright requests tweepy
playwright install chromium
```

### 3. Start the system

```bash
# Recommended: Gold Tier Orchestrator
python gold_tier_orchestrator.py

# Alternative: Full process launcher
python run_all.py

# Single workflow run
python run_all.py --once
```

### 4. Register CEO Briefing (optional)

```bash
python ceo_briefing_generator.py --schedule
```

### 5. Verify

```bash
python gold_tier_orchestrator.py --status   # System health
python process_watchdog.py --status          # Watcher status
python audit_logger.py --summary             # Audit summary
```

---

## Security

- `.env` is in `.gitignore` &mdash; never committed
- Odoo creates **DRAFT entries only** &mdash; human confirms all financial actions
- WhatsApp and LinkedIn session data stays local &mdash; never synced
- All outbound messages require **human approval**
- PKR 10,000+ transactions require **secondary approval**
- Rotate all API keys immediately if the directory is exposed

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| WhatsApp not connecting | `python whatsapp_watcher.py --setup` to re-authenticate |
| Gmail watcher failing | Verify `EMAIL_ADDRESS` and `EMAIL_APP_PASSWORD` in `.env` |
| Odoo connection refused | Confirm `ODOO_URL` is correct and Odoo service is running |
| Twitter API errors | Check your API v2 access tier and rate limits |
| Facebook/Instagram errors | Ensure Page Access Token has `pages_manage_posts` permission |
| CEO briefing is empty | Populate `silver_tier/Accounting/Current_Month.md` |
| Watchdog alerts | Check `logs/{process_name}.log` for error details |
| MCP servers not loading | Verify `.mcp.json` is present and Claude Code is restarted |

---

## Project Structure

```
gold-tier-ai-employee/
|-- silver_tier/                  # Obsidian vault (data store)
|   |-- Needs_Action/             # Incoming tasks
|   |-- Plans/                    # AI-generated action plans
|   |-- Pending_Approval/         # Awaiting human review
|   |-- Approved/                 # Ready for execution
|   |-- Done/                     # Completed and archived
|   |-- Logs/                     # Audit logs (YYYY-MM-DD.json)
|   |-- Briefings/                # CEO briefing files
|   |-- Invoices/                 # Generated invoices
|   |-- Accounting/               # Financial data
|   +-- In_Progress/              # Active tasks
|
|-- MCP Servers (10)
|   |-- linkedin_personal_mcp.py  # LinkedIn personal
|   |-- linkedin_company_mcp.py   # LinkedIn company
|   |-- email_mcp.py              # Gmail SMTP
|   |-- twitter_mcp.py            # Twitter/X
|   |-- facebook_instagram_mcp.py # Facebook + Instagram
|   |-- odoo_mcp.py               # Odoo ERP (13 tools)
|   |-- filesystem_mcp.py         # Vault operations
|   |-- browser_mcp.py            # Web automation
|   |-- calendar_mcp.py           # Google Calendar
|   +-- slack_mcp.py              # Slack messaging
|
|-- Core Engine
|   |-- gold_tier_orchestrator.py # Master orchestrator
|   |-- workflow_runner.py        # Processing loop
|   |-- inbox_planner.py          # Task planning
|   |-- approval_executor.py      # Action execution
|   |-- audit_logger.py           # JSON audit logging
|   |-- error_handler.py          # Retry logic
|   |-- ceo_briefing_generator.py # Weekly briefings
|   +-- process_watchdog.py       # Health monitoring
|
|-- Watchers
|   |-- gmail_oauth_watcher.py    # Gmail monitor
|   +-- whatsapp_watcher.py       # WhatsApp monitor
|
|-- .claude/
|   |-- skills/                   # 16 agent skills
|   +-- hooks/stop.py             # Ralph Wiggum stop hook
|
|-- .mcp.json                     # MCP server configuration
|-- .env.example                  # Environment template
+-- run_all.py                    # Process launcher
```

---

## License

This project was built for the **Personal AI Employee Hackathon**.

---

<p align="center">
  Built by <strong>Ubaid ur Rahman</strong>
</p>
