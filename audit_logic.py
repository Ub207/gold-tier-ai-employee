#!/usr/bin/env python3
"""
audit_logic.py — Subscription & Bank Transaction Audit Logic

Used by ceo_briefing_generator.py to:
  - Identify subscription charges from bank transactions
  - Flag unused or high-cost subscriptions
  - Categorize expenses automatically
  - Detect duplicate services

Usage (standalone):
    python audit_logic.py --file silver_tier/Accounting/Bank_Transactions.md
    python audit_logic.py --summary

Or import in other scripts:
    from audit_logic import analyze_transaction, audit_subscriptions, load_transactions
"""

import argparse
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Subscription pattern dictionary
# Map domain/keyword fragments → human-readable service name and category
# ---------------------------------------------------------------------------

SUBSCRIPTION_PATTERNS = {
    # --- Entertainment ---
    "netflix":        {"name": "Netflix",              "category": "Entertainment"},
    "spotify":        {"name": "Spotify",              "category": "Entertainment"},
    "youtube premium":{"name": "YouTube Premium",      "category": "Entertainment"},
    "apple music":    {"name": "Apple Music",           "category": "Entertainment"},
    "deezer":         {"name": "Deezer",                "category": "Entertainment"},
    "amazon prime":   {"name": "Amazon Prime",          "category": "Entertainment"},
    "disney":         {"name": "Disney+",               "category": "Entertainment"},

    # --- Productivity / SaaS ---
    "notion.so":      {"name": "Notion",                "category": "Productivity"},
    "notion":         {"name": "Notion",                "category": "Productivity"},
    "airtable":       {"name": "Airtable",              "category": "Productivity"},
    "monday.com":     {"name": "Monday.com",            "category": "Productivity"},
    "clickup":        {"name": "ClickUp",               "category": "Productivity"},
    "trello":         {"name": "Trello",                "category": "Productivity"},
    "asana":          {"name": "Asana",                 "category": "Productivity"},
    "zapier":         {"name": "Zapier",                "category": "Automation"},
    "make.com":       {"name": "Make (Integromat)",     "category": "Automation"},
    "n8n":            {"name": "n8n",                   "category": "Automation"},

    # --- Communication ---
    "slack.com":      {"name": "Slack",                 "category": "Communication"},
    "slack":          {"name": "Slack",                 "category": "Communication"},
    "zoom":           {"name": "Zoom",                  "category": "Communication"},
    "loom":           {"name": "Loom",                  "category": "Communication"},
    "calendly":       {"name": "Calendly",              "category": "Communication"},

    # --- Design / Creative ---
    "adobe":          {"name": "Adobe Creative Cloud",  "category": "Design"},
    "figma":          {"name": "Figma",                 "category": "Design"},
    "canva":          {"name": "Canva",                 "category": "Design"},
    "midjourney":     {"name": "Midjourney",            "category": "AI/Design"},
    "dalle":          {"name": "DALL-E",                "category": "AI/Design"},

    # --- Hosting / Infrastructure ---
    "aws":            {"name": "Amazon Web Services",   "category": "Infrastructure"},
    "digitalocean":   {"name": "DigitalOcean",          "category": "Infrastructure"},
    "vultr":          {"name": "Vultr",                 "category": "Infrastructure"},
    "linode":         {"name": "Linode/Akamai",         "category": "Infrastructure"},
    "heroku":         {"name": "Heroku",                "category": "Infrastructure"},
    "vercel":         {"name": "Vercel",                "category": "Infrastructure"},
    "netlify":        {"name": "Netlify",               "category": "Infrastructure"},
    "github":         {"name": "GitHub",                "category": "Dev Tools"},
    "gitlab":         {"name": "GitLab",                "category": "Dev Tools"},
    "cloudflare":     {"name": "Cloudflare",            "category": "Infrastructure"},

    # --- AI / LLM Tools ---
    "anthropic":      {"name": "Anthropic / Claude",    "category": "AI Tools"},
    "openai":         {"name": "OpenAI / ChatGPT",      "category": "AI Tools"},
    "claude":         {"name": "Claude Pro",            "category": "AI Tools"},
    "chatgpt":        {"name": "ChatGPT Plus",          "category": "AI Tools"},
    "perplexity":     {"name": "Perplexity AI",         "category": "AI Tools"},
    "jasper":         {"name": "Jasper AI",             "category": "AI Tools"},

    # --- Marketing / Analytics ---
    "mailchimp":      {"name": "Mailchimp",             "category": "Marketing"},
    "convertkit":     {"name": "ConvertKit",            "category": "Marketing"},
    "sendinblue":     {"name": "Brevo/Sendinblue",      "category": "Marketing"},
    "hubspot":        {"name": "HubSpot",               "category": "CRM"},
    "salesforce":     {"name": "Salesforce",            "category": "CRM"},
    "semrush":        {"name": "SEMrush",               "category": "Marketing"},
    "ahrefs":         {"name": "Ahrefs",                "category": "Marketing"},

    # --- Finance / Accounting ---
    "quickbooks":     {"name": "QuickBooks",            "category": "Accounting"},
    "xero":           {"name": "Xero",                  "category": "Accounting"},
    "freshbooks":     {"name": "FreshBooks",            "category": "Accounting"},
    "stripe":         {"name": "Stripe (fees)",         "category": "Payment Processing"},
    "paypal":         {"name": "PayPal (fees)",         "category": "Payment Processing"},

    # --- Domain / Email Hosting ---
    "namecheap":      {"name": "Namecheap",             "category": "Domains"},
    "godaddy":        {"name": "GoDaddy",               "category": "Domains"},
    "gsuite":         {"name": "Google Workspace",      "category": "Email Hosting"},
    "google workspace":{"name": "Google Workspace",     "category": "Email Hosting"},
    "microsoft 365":  {"name": "Microsoft 365",         "category": "Email Hosting"},
    "zoho":           {"name": "Zoho",                  "category": "Business Suite"},
}

# ---------------------------------------------------------------------------
# Expense category patterns (for non-subscription charges)
# ---------------------------------------------------------------------------

EXPENSE_CATEGORIES = {
    "uber":       "Travel",
    "careem":     "Travel",
    "grab":       "Travel",
    "fuel":       "Travel",
    "petrol":     "Travel",
    "restaurant": "Food",
    "cafe":       "Food",
    "coffee":     "Food",
    "lunch":      "Food",
    "dinner":     "Food",
    "grocery":    "Food/Groceries",
    "superstore": "Food/Groceries",
    "imtiaz":     "Food/Groceries",
    "metro":      "Food/Groceries",
    "daraz":      "Shopping",
    "amazon":     "Shopping",
    "salary":     "Payroll",
    "freelancer": "Payroll/Contractor",
    "upwork":     "Payroll/Contractor",
    "internet":   "Utilities",
    "electricity":"Utilities",
    "water":      "Utilities",
    "gas bill":   "Utilities",
    "office rent":"Rent",
    "rent":       "Rent",
    "tax":        "Tax",
    "fbr":        "Tax",
    "insurance":  "Insurance",
}

# ---------------------------------------------------------------------------
# Core analysis functions
# ---------------------------------------------------------------------------

def analyze_transaction(transaction: dict) -> dict | None:
    """
    Analyze a single bank transaction and return structured info.

    Expected transaction format:
    {
        "date": "2026-03-01",
        "description": "NETFLIX.COM 14.99 USD",
        "amount": 4200,        # PKR
        "type": "debit"        # or "credit"
    }

    Returns dict with type, name, category, or None if unrecognized.
    """
    desc = transaction.get("description", "").lower()
    amount = transaction.get("amount", 0)
    date = transaction.get("date", "")
    tx_type = transaction.get("type", "debit")

    # Check subscription patterns
    for pattern, info in SUBSCRIPTION_PATTERNS.items():
        if pattern in desc:
            return {
                "type": "subscription",
                "name": info["name"],
                "category": info["category"],
                "amount": amount,
                "date": date,
                "raw_description": transaction.get("description", ""),
                "transaction_type": tx_type,
            }

    # Check expense categories
    for pattern, category in EXPENSE_CATEGORIES.items():
        if pattern in desc:
            return {
                "type": "expense",
                "name": transaction.get("description", ""),
                "category": category,
                "amount": amount,
                "date": date,
                "raw_description": transaction.get("description", ""),
                "transaction_type": tx_type,
            }

    # Revenue / income
    if tx_type == "credit":
        return {
            "type": "income",
            "name": transaction.get("description", ""),
            "category": "Revenue",
            "amount": amount,
            "date": date,
            "raw_description": transaction.get("description", ""),
            "transaction_type": "credit",
        }

    return {
        "type": "uncategorized",
        "name": transaction.get("description", ""),
        "category": "Other",
        "amount": amount,
        "date": date,
        "raw_description": transaction.get("description", ""),
        "transaction_type": tx_type,
    }


def load_transactions(file_path: str | Path) -> list[dict]:
    """
    Parse transactions from Bank_Transactions.md markdown table.

    Expected table format:
    | Date       | Description                  | Amount (PKR) | Type   |
    |------------|------------------------------|--------------|--------|
    | 2026-03-01 | NETFLIX.COM                  | 4200         | debit  |
    """
    path = Path(file_path)
    if not path.exists():
        return []

    transactions = []
    in_table = False

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            in_table = False
            continue

        cells = [c.strip() for c in line.split("|") if c.strip()]
        if not cells:
            continue

        # Skip header and separator rows
        if cells[0].lower() in ("date", "---", ":---", "---:"):
            in_table = True
            continue
        if all(c.startswith("-") or c == "---" or c == ":---:" for c in cells):
            continue

        if len(cells) >= 3:
            try:
                amount_str = re.sub(r"[^\d.]", "", cells[2])
                amount = float(amount_str) if amount_str else 0.0
                tx_type = cells[3].lower() if len(cells) > 3 else "debit"
                transactions.append({
                    "date": cells[0],
                    "description": cells[1],
                    "amount": amount,
                    "type": tx_type,
                })
            except (ValueError, IndexError):
                continue

    return transactions


def audit_subscriptions(transactions: list[dict], last_login_days: int = 30) -> dict:
    """
    Run a full subscription audit.

    Returns:
    {
        "subscriptions": [...],          # all identified subscriptions
        "monthly_total": float,
        "flagged": [...],                # potentially unused / duplicates
        "categories": {...},             # spend by category
        "total_spend": float,
        "total_income": float,
    }
    """
    subscriptions = {}
    categories = {}
    total_spend = 0.0
    total_income = 0.0

    for tx in transactions:
        analyzed = analyze_transaction(tx)
        if not analyzed:
            continue

        if analyzed["transaction_type"] == "credit":
            total_income += analyzed["amount"]
            continue

        total_spend += analyzed["amount"]
        cat = analyzed.get("category", "Other")
        categories[cat] = categories.get(cat, 0) + analyzed["amount"]

        if analyzed["type"] == "subscription":
            name = analyzed["name"]
            if name not in subscriptions:
                subscriptions[name] = {
                    "name": name,
                    "category": analyzed["category"],
                    "total_paid": 0,
                    "occurrences": 0,
                    "last_seen": "",
                    "dates": [],
                }
            subscriptions[name]["total_paid"] += analyzed["amount"]
            subscriptions[name]["occurrences"] += 1
            subscriptions[name]["last_seen"] = analyzed["date"]
            subscriptions[name]["dates"].append(analyzed["date"])

    # Flag suspicious subscriptions
    flagged = []
    sub_list = list(subscriptions.values())

    # Check for duplicates in same category
    by_category = {}
    for sub in sub_list:
        cat = sub["category"]
        by_category.setdefault(cat, []).append(sub["name"])

    for cat, names in by_category.items():
        if len(names) > 1 and cat not in ("Infrastructure", "Dev Tools"):
            for name in names:
                flagged.append({
                    "name": name,
                    "reason": f"Duplicate functionality — {len(names)} services in '{cat}': {', '.join(names)}",
                    "severity": "medium",
                })

    # Flag high-cost subscriptions (> PKR 5,000/month)
    for sub in sub_list:
        monthly_est = sub["total_paid"] / max(sub["occurrences"], 1)
        if monthly_est > 5000:
            flagged.append({
                "name": sub["name"],
                "reason": f"High cost — estimated PKR {monthly_est:,.0f}/month",
                "severity": "high",
            })

    # Apply subscription audit rules from Business_Goals.md
    # (Rule: flag if no login in 30 days — here we flag if last seen > 30 days ago)
    cutoff = (datetime.now() - timedelta(days=last_login_days)).strftime("%Y-%m-%d")
    for sub in sub_list:
        if sub["last_seen"] and sub["last_seen"] < cutoff:
            flagged.append({
                "name": sub["name"],
                "reason": f"Last charge was {sub['last_seen']} — possibly unused for {last_login_days}+ days",
                "severity": "low",
            })

    # Deduplicate flagged list
    seen = set()
    unique_flagged = []
    for f in flagged:
        key = (f["name"], f["reason"][:40])
        if key not in seen:
            seen.add(key)
            unique_flagged.append(f)

    monthly_total = sum(
        sub["total_paid"] / max(sub["occurrences"], 1) for sub in sub_list
    )

    return {
        "subscriptions": sub_list,
        "monthly_total": monthly_total,
        "flagged": unique_flagged,
        "categories": categories,
        "total_spend": total_spend,
        "total_income": total_income,
    }


def format_audit_report(audit_result: dict, period: str = "current period") -> str:
    """Format the audit result as a markdown section for CEO briefing."""
    lines = [f"\n## Subscription Audit — {period}\n"]

    subs = audit_result.get("subscriptions", [])
    if subs:
        lines.append(f"**Active subscriptions:** {len(subs)}  ")
        lines.append(f"**Estimated monthly cost:** PKR {audit_result['monthly_total']:,.0f}\n")
        lines.append("| Service | Category | Est. Monthly (PKR) | Occurrences |")
        lines.append("|---------|----------|-------------------|-------------|")
        for sub in sorted(subs, key=lambda x: -x["total_paid"]):
            monthly = sub["total_paid"] / max(sub["occurrences"], 1)
            lines.append(
                f"| {sub['name']} | {sub['category']} | "
                f"PKR {monthly:,.0f} | {sub['occurrences']}x |"
            )
    else:
        lines.append("No subscription charges found in transactions.\n")

    flagged = audit_result.get("flagged", [])
    if flagged:
        lines.append(f"\n### ⚠️ Flagged for Review ({len(flagged)} items)\n")
        for f in flagged:
            icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(f["severity"], "•")
            lines.append(f"- {icon} **{f['name']}** — {f['reason']}")

    cats = audit_result.get("categories", {})
    if cats:
        lines.append("\n### Spend by Category\n")
        lines.append("| Category | PKR |")
        lines.append("|----------|-----|")
        for cat, amt in sorted(cats.items(), key=lambda x: -x[1]):
            lines.append(f"| {cat} | PKR {amt:,.0f} |")

    lines.append(
        f"\n**Total spend:** PKR {audit_result['total_spend']:,.0f}  \n"
        f"**Total income:** PKR {audit_result['total_income']:,.0f}  \n"
        f"**Net:** PKR {audit_result['total_income'] - audit_result['total_spend']:,.0f}"
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Subscription & bank transaction audit")
    parser.add_argument(
        "--file",
        default="silver_tier/Accounting/Bank_Transactions.md",
        help="Path to Bank_Transactions.md (default: silver_tier/Accounting/Bank_Transactions.md)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print audit summary to stdout",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of markdown",
    )
    args = parser.parse_args()

    transactions = load_transactions(args.file)

    if not transactions:
        print(f"No transactions found in {args.file}")
        print("Make sure Bank_Transactions.md exists with a valid table.")
        return

    result = audit_subscriptions(transactions)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        report = format_audit_report(result)
        print(report)

        print(f"\n--- Summary ---")
        print(f"Transactions analysed : {len(transactions)}")
        print(f"Subscriptions found   : {len(result['subscriptions'])}")
        print(f"Flagged for review    : {len(result['flagged'])}")
        print(f"Total spend           : PKR {result['total_spend']:,.0f}")
        print(f"Total income          : PKR {result['total_income']:,.0f}")
        print(f"Est. monthly subs     : PKR {result['monthly_total']:,.0f}")


if __name__ == "__main__":
    import io
    import sys as _sys
    if hasattr(_sys.stdout, "buffer"):
        _sys.stdout = io.TextIOWrapper(_sys.stdout.buffer, encoding="utf-8", errors="replace")
    main()
