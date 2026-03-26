<p align="center">
  <img src="https://img.shields.io/badge/Tier-Gold-FFD700?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Status-Production-brightgreen?style=for-the-badge" />
  <img src="https://img.shields.io/badge/MCP_Servers-10-blue?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Python-3.9+-yellow?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Claude-Opus_4-FF6B35?style=for-the-badge&logo=anthropic&logoColor=white" />
</p>

<h1 align="center">AI Employee - Gold Tier</h1>
<p align="center"><strong>Advanced multi-platform automation with 10 MCP servers, Odoo ERP, and weekly CEO briefings.</strong></p>

---

## What Gold Tier Adds

Building on Silver Tier's email/LinkedIn/WhatsApp automation, Gold Tier adds **6 new integrations** and **enterprise-grade features**:

| New in Gold | Description |
|------------|------------|
| **Twitter/X** | Tweet posting, timeline monitoring, search |
| **Facebook** | Page posts, engagement tracking |
| **Instagram** | Image posts, content management |
| **Slack** | Messages, channels, file uploads, status updates |
| **Odoo ERP** | 13 tools: invoices, payments, vendors, partners, accounting |
| **Google Calendar** | Events, free slots, scheduling |
| **CEO Briefing** | Auto-generated weekly business report |
| **Audit Logging** | Full JSON audit trail for every action |
| **Error Handling** | Retry with exponential backoff |

---

## 10 MCP Server Integrations

```
  linkedin ──────── Personal & Company page posts
  email ─────────── Gmail: send, read, search, draft (OAuth2)
  twitter ────────── Tweet, timeline, search
  facebook-ig ───── Facebook + Instagram posts
  odoo ────────────── 13 ERP tools
  filesystem ────── Vault read/write/search
  browser ─────────── Web automation
  calendar ────────── Google Calendar CRUD
  slack ─────────── Messages, channels, status
```

## Odoo ERP Integration (13 Tools)

| Tool | Function |
|------|---------|
| `odoo_create_invoice` | Create draft invoice |
| `odoo_post_invoice` | Post confirmed invoice |
| `odoo_list_invoices` | List all invoices |
| `odoo_create_vendor_bill` | Create vendor bill |
| `odoo_create_payment_draft` | Create payment draft |
| `odoo_confirm_payment` | Confirm payment |
| `odoo_list_payments` | List all payments |
| `odoo_get_overdue_invoices` | Get overdue invoices |
| `odoo_create_payment_followup` | Auto follow-up on overdue |
| `odoo_create_partner` | Create new partner/contact |
| `odoo_get_partner` | Get partner details |
| `odoo_get_account_summary` | Account summary |
| `odoo_get_revenue_summary` | Revenue summary |

## CEO Briefing

Auto-generated every Monday from vault data:
- Business goals progress
- Revenue & accounting summary
- Completed tasks this week
- Pending items & blockers
- Action items for the week

---

## Architecture

```
Watchers (Gmail, WhatsApp, Filesystem)
        │
        ▼
Needs_Action/ ──► inbox_planner.py ──► Plans/
        │
        ▼
Pending_Approval/ (human reviews in Obsidian)
        │
   ┌────┴────┐
   ▼         ▼
Approved/  Rejected/
   │
   ▼
approval_executor.py ──► MCP Servers ──► Done/
   │
   ▼
audit_logger.py ──► Dashboard.md updated
```

---

## Key Scripts

| Script | Purpose |
|--------|---------|
| `gold_tier_orchestrator.py` | Main orchestrator |
| `gmail_oauth_watcher.py` | Email monitoring |
| `whatsapp_watcher.py` | WhatsApp monitoring |
| `workflow_runner.py` | Processing loop (every 5 min) |
| `approval_executor.py` | Execute approved items |
| `ceo_briefing_generator.py` | Weekly CEO briefing |
| `audit_logger.py` | JSON audit trail |
| `error_handler.py` | Retry with backoff |

---

## Quick Start

```bash
git clone https://github.com/Ub207/gold-tier-ai-employee.git
cd gold-tier-ai-employee
pip install -r requirements.txt
cp .env.example .env  # Add your API keys
python gold_tier_orchestrator.py
```

---

<p align="center">
  <strong>Built by <a href="https://github.com/Ub207">Ubaid ur Rahman</a></strong><br/>
  AI Automation Consulting | <a href="mailto:usmanubaidurrehman@gmail.com">Hire Me</a>
</p>
