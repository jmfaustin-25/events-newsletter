# Second Curves : Media and Events Brief

A professional newsletter generator for the **global B2B trade press, conferences, exhibitions, and events industry**.

Written in **FT/Economist style**: strategic, analytical, board-level intelligence — designed for **investors, board directors, and senior executives** who want signals, not noise.

---

## What you get

A clean HTML (or Markdown) newsletter with three board-relevant sections:

| Section | Icon | Content |
|---------|------|---------|
| **Market Signals** | 📊 | Strategic trends, market movements, structural shifts |
| **Deals** | 🤝 | M&A, investments, private equity, divestitures |
| **Hires & Fires** | 👔 | Executive appointments, departures, restructuring |

---

## How it works (2-stage AI pipeline)

This generator runs in **two steps**:

1. **Filter + score (board lens):** Claude screens the raw feed + any user sources using board-level lenses (macro & capital, formats, geography, pricing/yield, M&A/portfolio moves, cost structure). It outputs a **ranked shortlist**.
2. **Write (FT/Economist style):** Claude writes the final newsletter **only from the shortlist**, focusing on “why this matters” and strategic implications.

This makes the newsletter tighter, more consistent, and less “trade-press round-up”.

---

## Quick Start

### Option 1: GitHub Actions (Recommended)

1. Fork this repository
2. Add your API key: **Settings → Secrets and variables → Actions → New repository secret**
   - Name: `ANTHROPIC_API_KEY`
   - Value: your Anthropic key
3. Go to **Actions → Run workflow** (or wait for the schedule)

> If your workflow uses environments/approvals, follow any repo-specific instructions in `.github/workflows/newsletter.yml`.

### Option 2: Local

```bash
pip install anthropic feedparser requests python-dateutil jinja2 beautifulsoup4
export ANTHROPIC_API_KEY="sk-ant-..."
python events_newsletter_generator.py --out-file newsletter.html
