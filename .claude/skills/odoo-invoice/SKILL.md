# Skill: odoo-invoice

Create and manage draft invoices in Odoo Community ERP. All accounting actions are DRAFT only — never auto-post.

## Trigger
- `/odoo-invoice` — create a new draft invoice
- `/odoo-invoice list` — list recent invoices
- `/odoo-invoice revenue` — get revenue summary from Odoo
- `/odoo-invoice partner [name]` — look up a partner/client record

---

## Hard Rules (Never Break)
- ALL Odoo writes are DRAFT only. Never confirm/post an invoice automatically.
- Approval required for every invoice action (per Company Handbook).
- Amounts > PKR 10,000 require secondary approval — flag clearly.
- Log every action to `silver_tier/Logs/YYYY-MM-DD.json`.

---

## Step 1 — Gather Invoice Details

Collect or ask for:
- Client name (search in Odoo with `mcp__odoo__odoo_get_partner`)
- Line items: description, quantity, unit price (PKR)
- Invoice date
- Due date (default: 30 days from invoice date)
- Reference / PO number (optional)

---

## Step 2 — Check Partner

Look up the client in Odoo:
```
mcp__odoo__odoo_get_partner(name="[client name]")
```

If partner not found, note: "Partner not in Odoo — will need to be created manually or partner_id will be null."

---

## Step 3 — Create Draft Invoice Plan

Write plan to `silver_tier/Plans/INV_[YYYYMMDD_HHMM]_[client_slug].md`:

```markdown
---
type: odoo_invoice
created: [YYYY-MM-DD HH:MM:SS]
status: draft
client: [client name]
amount_total: [PKR total]
secondary_approval_required: [yes if > PKR 10,000 else no]
---

## Invoice Details
- Client: [name]
- Partner ID: [id or "not found"]
- Invoice Date: [date]
- Due Date: [date]

## Line Items
| Description | Qty | Unit Price (PKR) | Subtotal (PKR) |
|-------------|-----|-----------------|----------------|
| [item] | [qty] | [price] | [subtotal] |
| **TOTAL** | | | **[total]** |

## Approval Required
> ⚠️ Amount: PKR [total] — [secondary approval note if > 10,000]

## To Create
1. Move this file to `silver_tier/Approved/`
2. Run: `/odoo-invoice create [filename]`
```

---

## Step 4 — Route to Pending_Approval

Copy file to `silver_tier/Pending_Approval/`. Print:
```
=== Odoo Invoice Draft Ready ===
Client:  [name]
Amount:  PKR [total]
Plan:    silver_tier/Plans/[filename]
Pending: silver_tier/Pending_Approval/[filename]
[⚠️ SECONDARY APPROVAL REQUIRED if > PKR 10,000]

Next steps:
  1. Review plan in Obsidian
  2. Move to Approved/ if correct
  3. Run: /odoo-invoice create [filename]
================================
```

---

## Step 5 — Create in Odoo (after approval)

Human moved file to `Approved/`. Call:
```
mcp__odoo__odoo_create_invoice(
  partner_id=[id],
  lines=[{"name": "...", "quantity": 1, "price_unit": ...}],
  invoice_date="[YYYY-MM-DD]"
)
```

Result is always a DRAFT invoice in Odoo. Print the invoice ID.

On success:
- Log to `silver_tier/Logs/YYYY-MM-DD.json` (action: `invoice_created`)
- Save invoice record to `silver_tier/Invoices/INV_[date]_[client].md`
- Move plan: `Approved/` → `Done/`

---

## Step 6 — Revenue Summary

```
mcp__odoo__odoo_get_revenue_summary()
```

Display:
- Total invoiced (current month)
- Paid vs unpaid
- Top clients by revenue
- Overdue invoices

---

## Required Env Vars
```
ODOO_URL=http://localhost:8069
ODOO_DB=
ODOO_USERNAME=
ODOO_PASSWORD=
```
