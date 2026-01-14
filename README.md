# Events Industry Intelligence Newsletter

A professional newsletter generator for the **global B2B trade press, conferences, exhibitions, and events industry**.

Written in **FT/Economist style** - strategic, analytical, board-level intelligence.

## Sections

| Section | Icon | Content |
|---------|------|---------|
| **Market Signals** | 📊 | Strategic trends, market movements, analysis |
| **Deals** | 🤝 | M&A, investments, private equity, divestitures |
| **Hires & Fires** | 👔 | Executive appointments, departures, restructuring |

## Quick Start

### Option 1: GitHub Actions (Recommended)

1. Fork this repository
2. Add your API key: **Settings → Secrets → ANTHROPIC_API_KEY**
3. Create environment: **Settings → Environments → newsletter-approval** (add yourself as reviewer)
4. Go to **Actions → Run workflow**

### Option 2: Local

```bash
pip install anthropic feedparser requests python-dateutil jinja2 beautifulsoup4
export ANTHROPIC_API_KEY="sk-ant-..."
python events_newsletter_generator.py --out-file newsletter.html
```

## Adding Your Own Sources

Create a `sources/` folder in the repository with your collected articles:

```
sources/
├── urls.txt              # List of URLs (one per line)
├── informa-acquisition.txt   # Article text you've copied
├── executive-moves.json      # Structured data
└── analysis.md              # Your own analysis/notes
```

### Supported Formats

**URLs file** (`*.txt` with URLs):
```
https://example.com/article-1
https://example.com/article-2
```

**Article text** (`*.txt`):
```
Just paste the article content here.
The filename becomes the title.
```

**JSON** (`*.json`):
```json
[
  {
    "title": "Informa acquires Tarsus",
    "source": "Financial Times",
    "content": "Informa has agreed to acquire...",
    "link": "https://ft.com/..."
  }
]
```

**Markdown** (`*.md`):
```markdown
# My Analysis of RX France Sale

The sale signals a broader trend...
```

**User-provided sources are prioritized** - Claude will ensure they're considered for inclusion.

## Customizing RSS Feeds

Edit `events_newsletter_generator.py` and modify the `RSS_FEEDS` dictionary:

```python
RSS_FEEDS = {
    # Add your preferred sources
    "my_source": "https://example.com/feed.xml",
    
    # Comment out sources you don't want
    # "exhibition_world": "...",
}
```

### Suggested Additional Feeds

```python
# Regional
"mice_asia": "https://www.micenet.asia/feed/",
"exhibition_world_asia": "https://www.exhibitionworld.asia/feed",

# Trade associations
"ufi_news": "https://www.ufi.org/feed/",
"iaee_news": "https://www.iaee.com/feed/",

# Business press (for M&A)
"ft_media": "https://www.ft.com/companies/media?format=rss",
"reuters_media": "https://www.reuters.com/news/archive/mediaNews?format=rss",
```

## Editing the Writing Style

The `WRITING_STYLE` variable in the script controls Claude's tone. Current settings:

- **Tone**: Authoritative, analytical (FT/Economist style)
- **Structure**: Lead with significance, short paragraphs
- **Language**: No hyperbole, no marketing speak, precise

To adjust, edit the `WRITING_STYLE` string in the script.

## Section Configuration

Each section has keywords that help Claude categorize stories:

```python
SECTIONS = {
    "market_signals": {
        "keywords": ["market", "growth", "expansion", "partnership", ...],
        "prompt_focus": "Focus on strategic market movements..."
    },
    ...
}
```

## Workflow Options

When running via GitHub Actions, you can customize:

| Option | Description | Example |
|--------|-------------|---------|
| `days_back` | How far to look for news | 7, 14, 30 |
| `stories_per_section` | Main stories per section | 2-5 |
| `focus_section` | Emphasize a specific section | "deals" |
| `custom_instructions` | Tell Claude what you want | "Focus on European market" |
| `regenerate_feedback` | What to fix from last draft | "Remove Informa story, add more hires" |

## Example Custom Instructions

| Goal | What to Type |
|------|--------------|
| Regional focus | "Focus on European and UK market news" |
| Specific companies | "Include any news about Informa, RX, or Clarion" |
| Skip a topic | "Don't include sustainability stories this week" |
| More analysis | "Add more strategic analysis, less news summary" |
| Different tone | "Slightly more conversational, but still professional" |

## File Structure

```
your-repo/
├── events_newsletter_generator.py   # Main script
├── README.md                        # This file
├── sources/                         # Your collected sources (optional)
│   ├── urls.txt
│   └── *.json, *.txt, *.md
├── newsletters/                     # Published newsletters (auto-created)
│   ├── latest.html
│   ├── latest.md
│   ├── 2025-01-13.html
│   └── ...
└── .github/
    └── workflows/
        └── newsletter.yml           # GitHub Actions workflow
```

## Costs

- **Claude API**: ~$0.05-0.15 per newsletter
- **GitHub Actions**: Free (2,000 minutes/month on free tier)
- **Total**: ~$2-5/month for weekly newsletters

## Troubleshooting

**"No articles found"**
- Check if RSS feeds are working (some may be blocked or changed)
- Try increasing `days_back`
- Add more sources to the `sources/` folder

**"JSON parse error"**
- Usually means Claude's response was cut off
- Try reducing `stories_per_section`

**Empty sections**
- Normal if no relevant news that period
- Add more RSS feeds or user sources

## License

MIT - use freely for your own newsletter.
