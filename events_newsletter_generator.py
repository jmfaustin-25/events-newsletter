#!/usr/bin/env python3
"""
The Second Curves Media & Events Brief - Newsletter Generator
--------------------------------------------------------------
A specialized newsletter for the global trade press, conference, 
and tradeshow market. Written in Axios style for board-level readers.

Sections:
1. Executive Summary - Key takeaways for investors, boards, portfolio directors
2. Market Signals - Macro Economy & Consumer Trends
3. Deals (M&A) - Mergers, acquisitions, investments, divestitures  
4. Hires & Fires - Executive appointments, departures, restructuring

Usage:
    python events_newsletter_generator.py
    python events_newsletter_generator.py --sources-folder ./my_sources
    python events_newsletter_generator.py --output html --out-file newsletter.html
    python events_newsletter_generator.py --list-articles  # Show all articles for review

Requirements:
    pip install anthropic feedparser requests python-dateutil jinja2 beautifulsoup4
"""

import argparse
import json
import os
import re
import glob
from pathlib import Path
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from typing import Optional, List, Dict
import feedparser
import requests
from anthropic import Anthropic

# =============================================================================
# CONFIGURATION
# =============================================================================

# Default recipient name (can be overridden)
DEFAULT_RECIPIENT_NAME = "Reader"

# Industry-specific RSS feeds for trade press, events, and exhibitions
RSS_FEEDS = {
    # Exhibition & Events Industry
    "exhibition_world": "https://www.exhibitionworld.co.uk/feed",
    "exhibition_news": "https://www.exhibitionnews.co.uk/feed",
    "mash_media": "https://www.mashmedia.net/feed/",
    "conference_news": "https://www.conference-news.co.uk/feed",
    "access_aa": "https://accessaa.co.uk/feed/",
    "eventindustrynews": "https://www.eventindustrynews.com/feed",
    "tsnn": "https://www.tsnn.com/feed",
    "exhibitor_online": "https://www.exhibitoronline.com/news/rss.xml",
    
    # B2B Media & Publishing
    "fipp": "https://www.fipp.com/feed/",
    "inpublishing": "https://www.inpublishing.co.uk/feed",
    "pressgazette": "https://pressgazette.co.uk/feed/",
    "journalism_co_uk": "https://www.journalism.co.uk/feed/",
    
    # Business News
    "pe_hub_media": "https://www.pehub.com/feed/",
    
    # Marketing & Events Adjacent
    "event_marketer": "https://www.eventmarketer.com/feed/",
    "bizbash": "https://www.bizbash.com/rss.xml",
    "skift_meetings": "https://skift.com/meetings/feed/",
}

# Axios-style writing configuration
WRITING_STYLE = """
WRITING STYLE - AXIOS EDITORIAL STANDARDS:

FORMAT:
- Use bullet points extensively
- Lead every story with "Why it matters:" or "The big picture:"
- Include "By the numbers:" when data is available
- Add "What to watch:" for forward-looking implications
- Keep bullets to 1-2 lines maximum

TONE:
- Direct and punchy - no filler words
- Assume reader has 30 seconds per story
- Every bullet must answer "So what?"
- Authoritative but accessible
- No marketing speak or hype

STRUCTURE FOR EACH STORY:
1. **Headline** - Clear, informative (not clickbait)
2. **Why it matters:** - Strategic significance in 1-2 bullets
3. **The details:** - Key facts in 2-3 bullets
4. **What to watch:** - Forward implications in 1 bullet

LANGUAGE:
- Active voice only
- Short sentences
- Precise numbers with context
- "Sources say" for unconfirmed info
- No exclamation marks
"""

# Executive Summary prompt
EXECUTIVE_SUMMARY_PROMPT = """You are the editor-in-chief of a board-level intelligence briefing covering the global B2B media, exhibitions, and events industry.

Write a concise EXECUTIVE SUMMARY for the newsletter.

AUDIENCE (write for all three simultaneously):
1. Investors (primarily private equity and strategic investors)
2. Board members of media and event businesses
3. Portfolio directors overseeing multiple media and event assets

TONE & FORMAT:
- Open with: "Good morning,"
- Professional, direct, and analytical
- No hype, no marketing language
- Assume reader spends 60-90 seconds on this section
- Use bullet points only (no paragraphs)
- Each bullet must answer "so what?"

CONTENT FILTERING:
Include only items that materially affect:
- Capital allocation
- Growth outlook
- Competitive positioning
- Portfolio strategy
- Operating leverage or margin structure

STRUCTURE:
**Good morning,**

[Single sentence setting context for the period]

**Key Takeaways for Investors**
- 3-5 bullets on market health, valuation signals, capital flows, M&A activity, risk factors
- Focus on entry/exit timing, multiples, platform vs bolt-on logic

**Key Takeaways for Boards**
- 3-5 bullets on strategic implications: growth drivers, threats, pricing power, format shifts
- Emphasise what boards should discuss or stress-test

**Key Takeaways for Portfolio Directors**
- 3-5 bullets on execution: competitor moves, geography bets, technology investments, talent
- Highlight patterns requiring cross-portfolio action

CONSTRAINTS:
- Do NOT summarise every article
- Do NOT repeat headlines
- Each bullet max 2 lines
- If weak signal in an area, state explicitly ("Limited evidence this period of...")
"""

# Section definitions
SECTIONS = {
    "market_signals": {
        "title": "Market Signals",
        "icon": "📊",
        "description": "Strategic trends, market movements, and industry analysis",
        "sub_themes": ["Macro Economy", "Consumer Trends"],
        "keywords": ["market", "growth", "revenue", "strategy", "expansion", "launch", 
                    "partnership", "trend", "forecast", "analysis", "report", "data",
                    "attendance", "exhibitors", "square feet", "square metres", "venue",
                    "digital", "hybrid", "sustainability", "AI", "technology",
                    "economy", "recession", "inflation", "GDP", "interest rates", "spending",
                    "consumer", "audience", "visitors", "attendees", "behavior", "demand"],
        "prompt_focus": "Strategic market movements. Organize under: (1) MACRO ECONOMY - economic conditions, recession, interest rates, corporate spending; (2) CONSUMER TRENDS - attendee behavior, visitor patterns, audience preferences."
    },
    "deals": {
        "title": "Deals",
        "icon": "🤝",
        "description": "Mergers, acquisitions, investments, and divestitures",
        "sub_themes": None,
        "keywords": ["acquisition", "acquire", "merger", "merge", "investment", "invest",
                    "private equity", "PE", "buy", "sell", "divest", "stake", "valuation",
                    "deal", "transaction", "purchase", "funding", "capital", "IPO",
                    "Informa", "RX", "Clarion", "Hyve", "Tarsus", "Emerald", "Endeavor"],
        "prompt_focus": "M&A activity, private equity moves, strategic investments, divestitures. Include deal values and strategic rationale."
    },
    "hires_fires": {
        "title": "Hires & Fires",
        "icon": "👔",
        "description": "Executive appointments, departures, and restructuring",
        "sub_themes": None,
        "keywords": ["CEO", "CFO", "COO", "CMO", "appointed", "appointment", "hire", "hired",
                    "join", "joined", "depart", "departure", "resign", "resignation", 
                    "retire", "retirement", "restructur", "layoff", "redundan", "chief",
                    "president", "director", "managing director", "MD", "VP", "executive"],
        "prompt_focus": "Senior executive movements (C-suite, MD, VP+). Analyze what appointments signal about strategy."
    }
}

# HTML Template - Axios style with Second Curve Consulting branding
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            max-width: 680px;
            margin: 0 auto;
            padding: 20px;
            background: #ffffff;
            color: #1a1a1a;
            line-height: 1.6;
            font-size: 16px;
        }
        .logo-banner {
            background: #7B8B70;
            padding: 25px 20px;
            text-align: center;
            border-radius: 8px 8px 0 0;
        }
        .logo-banner img {
            max-width: 260px;
            height: auto;
        }
        .header {
            background: #7B8B70;
            padding: 0 20px 20px 20px;
            margin-bottom: 25px;
            border-radius: 0 0 8px 8px;
            text-align: center;
        }
        .header h1 {
            font-size: 22px;
            font-weight: 800;
            margin: 0 0 5px 0;
            color: #ffffff;
        }
        .header .tagline {
            color: rgba(255,255,255,0.85);
            font-size: 13px;
            margin-bottom: 8px;
        }
        .header .date {
            font-size: 12px;
            color: rgba(255,255,255,0.7);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .executive-summary {
            background: #f8f9fa;
            border-left: 4px solid #7B8B70;
            padding: 20px;
            margin-bottom: 30px;
        }
        .executive-summary .greeting {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 15px;
        }
        .executive-summary h3 {
            font-size: 14px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #5a6b52;
            margin: 20px 0 10px 0;
            padding-top: 15px;
            border-top: 1px solid #ddd;
        }
        .executive-summary h3:first-of-type {
            border-top: none;
            padding-top: 0;
            margin-top: 10px;
        }
        .executive-summary ul {
            margin: 0;
            padding-left: 20px;
        }
        .executive-summary li {
            margin-bottom: 8px;
            line-height: 1.5;
        }
        .section {
            margin-bottom: 35px;
        }
        .section-header {
            display: flex;
            align-items: center;
            border-bottom: 2px solid #7B8B70;
            padding-bottom: 8px;
            margin-bottom: 20px;
        }
        .section-header h2 {
            font-size: 20px;
            font-weight: 800;
            margin: 0;
            color: #1a1a1a;
        }
        .section-header .icon {
            font-size: 18px;
            margin-right: 8px;
        }
        .sub-theme {
            font-size: 13px;
            font-weight: 700;
            color: #5a6b52;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin: 20px 0 12px 0;
            padding-bottom: 5px;
            border-bottom: 1px dashed #7B8B70;
        }
        .story {
            margin-bottom: 25px;
            padding-bottom: 20px;
            border-bottom: 1px solid #eee;
        }
        .story:last-child {
            border-bottom: none;
        }
        .story h3 {
            font-size: 18px;
            font-weight: 700;
            margin: 0 0 8px 0;
            line-height: 1.3;
        }
        .story .meta {
            font-size: 11px;
            color: #888;
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .story .label {
            font-weight: 700;
            color: #5a6b52;
            font-size: 12px;
            text-transform: uppercase;
            display: block;
            margin-top: 10px;
            margin-bottom: 4px;
        }
        .story ul {
            margin: 0 0 10px 0;
            padding-left: 18px;
        }
        .story li {
            margin-bottom: 5px;
            line-height: 1.5;
        }
        .story .source-link {
            font-size: 12px;
            color: #5a6b52;
            text-decoration: none;
            font-weight: 600;
        }
        .story .source-link:hover {
            text-decoration: underline;
        }
        .footer {
            background: #7B8B70;
            margin-top: 40px;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            font-size: 12px;
            color: rgba(255,255,255,0.8);
        }
        .footer a {
            color: #ffffff;
        }
        .no-stories {
            color: #888;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="logo-banner">
        {% if logo_url %}
        <img src="{{ logo_url }}" alt="Second Curve Consulting">
        {% else %}
        <div style="color: white; font-size: 24px; font-weight: bold;">SECOND CURVE CONSULTING</div>
        {% endif %}
    </div>
    <div class="header">
        <h1>{{ title }}</h1>
        <div class="tagline">Intelligence for the global B2B media, exhibitions & events industry</div>
        <div class="date">{{ date }}</div>
    </div>
    
    {% if executive_summary %}
    <div class="executive-summary">
        {{ executive_summary | safe }}
    </div>
    {% endif %}
    
    {% for section_key, section_data in sections.items() %}
    <div class="section">
        <div class="section-header">
            <span class="icon">{{ section_data.icon }}</span>
            <h2>{{ section_data.title }}</h2>
        </div>
        
        {% if section_data.stories %}
            {% if section_data.sub_themes %}
                {% for sub_theme in section_data.sub_themes %}
                <div class="sub-theme">{{ sub_theme }}</div>
                {% for story in section_data.stories %}
                {% if story.sub_theme == sub_theme %}
                <div class="story">
                    <h3>{{ story.headline }}</h3>
                    <div class="meta">{{ story.source }} • {{ story.published }}</div>
                    {{ story.summary | safe }}
                    {% if story.link %}
                    <a href="{{ story.link }}" class="source-link">Read source →</a>
                    {% endif %}
                </div>
                {% endif %}
                {% endfor %}
                {% endfor %}
            {% else %}
                {% for story in section_data.stories %}
                <div class="story">
                    <h3>{{ story.headline }}</h3>
                    <div class="meta">{{ story.source }} • {{ story.published }}</div>
                    {{ story.summary | safe }}
                    {% if story.link %}
                    <a href="{{ story.link }}" class="source-link">Read source →</a>
                    {% endif %}
                </div>
                {% endfor %}
            {% endif %}
        {% else %}
            <p class="no-stories">No significant {{ section_data.title.lower() }} this period.</p>
        {% endif %}
    </div>
    {% endfor %}
    
    <div class="footer">
        {{ footer_text | default('Published by Second Curve Consulting') }}<br>
        <a href="https://secondcurveconsulting.com">secondcurveconsulting.com</a>
    </div>
</body>
</html>
"""

# Markdown Template - Axios style
MARKDOWN_TEMPLATE = """# {{ title }}

*Intelligence for the global B2B media, exhibitions & events industry*

**{{ date }}**

---

{% if executive_summary %}
{{ executive_summary }}

---
{% endif %}

{% for section_key, section_data in sections.items() %}
## {{ section_data.icon }} {{ section_data.title }}

{% if section_data.stories %}
{% if section_data.sub_themes %}
{% for sub_theme in section_data.sub_themes %}
### {{ sub_theme }}

{% for story in section_data.stories %}
{% if story.sub_theme == sub_theme %}
#### {{ story.headline }}

*{{ story.source }} • {{ story.published }}*

{{ story.summary }}

{% if story.link %}[Read source →]({{ story.link }}){% endif %}

---

{% endif %}
{% endfor %}
{% endfor %}
{% else %}
{% for story in section_data.stories %}
### {{ story.headline }}

*{{ story.source }} • {{ story.published }}*

{{ story.summary }}

{% if story.link %}[Read source →]({{ story.link }}){% endif %}

---

{% endfor %}
{% endif %}

{% else %}
*No significant {{ section_data.title.lower() }} this period.*
{% endif %}

{% endfor %}

---

*{{ footer_text | default('Published by Second Curves') }}*
"""

# =============================================================================
# CORE FUNCTIONS
# =============================================================================

def fetch_feeds(feeds: dict, days_back: int = 7) -> list:
    """Fetch and parse RSS feeds, returning articles from the last N days."""
    cutoff_date = datetime.now() - timedelta(days=days_back)
    articles = []
    
    for source_name, feed_url in feeds.items():
        try:
            print(f"  Fetching {source_name}...")
            
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            try:
                response = requests.get(feed_url, headers=headers, timeout=15)
                feed = feedparser.parse(response.content)
            except:
                feed = feedparser.parse(feed_url)
            
            if not feed.entries:
                print(f"    ⚠️  No entries found")
                continue
                
            for entry in feed.entries[:15]:
                pub_date = None
                for date_field in ['published', 'updated', 'created', 'pubDate']:
                    if hasattr(entry, date_field):
                        try:
                            pub_date = date_parser.parse(getattr(entry, date_field))
                            if pub_date.tzinfo:
                                pub_date = pub_date.replace(tzinfo=None)
                            break
                        except:
                            continue
                
                if not pub_date:
                    pub_date = datetime.now()
                
                if pub_date < cutoff_date:
                    continue
                
                content = ""
                if hasattr(entry, 'summary'):
                    content = entry.summary
                elif hasattr(entry, 'description'):
                    content = entry.description
                elif hasattr(entry, 'content'):
                    content = entry.content[0].value if entry.content else ""
                
                content = re.sub(r'<[^>]+>', '', content)
                content = re.sub(r'\s+', ' ', content).strip()
                content = content[:2000]
                
                articles.append({
                    "source": source_name.replace("_", " ").title(),
                    "title": entry.get('title', 'Untitled'),
                    "link": entry.get('link', ''),
                    "content": content,
                    "published": pub_date.strftime("%d %B %Y"),
                    "pub_timestamp": pub_date.timestamp(),
                    "from_user_sources": False
                })
                
        except Exception as e:
            print(f"    ⚠️  Error: {e}")
    
    articles.sort(key=lambda x: x['pub_timestamp'], reverse=True)
    print(f"  ✓ Fetched {len(articles)} articles from RSS feeds")
    return articles


def load_user_sources(sources_folder: str) -> list:
    """Load articles from user-provided sources folder."""
    articles = []
    folder = Path(sources_folder)
    
    if not folder.exists():
        print(f"  Sources folder not found: {sources_folder}")
        return articles
    
    print(f"  Loading user sources from {sources_folder}...")
    
    # Process all subfolders too
    for subfolder in [folder] + list(folder.iterdir()):
        if not subfolder.is_dir():
            continue
            
        # Process text files
        for txt_file in subfolder.glob("*.txt"):
            try:
                content = txt_file.read_text(encoding='utf-8')
                lines = content.strip().split('\n')
                
                if all(line.strip().startswith(('http://', 'https://')) for line in lines if line.strip()):
                    for url in lines:
                        url = url.strip()
                        if url and not url.startswith('#'):
                            articles.append({
                                "source": "User Source",
                                "title": f"Source: {url[:50]}...",
                                "link": url,
                                "content": f"[User-provided URL: {url}]",
                                "published": datetime.now().strftime("%d %B %Y"),
                                "pub_timestamp": datetime.now().timestamp(),
                                "from_user_sources": True
                            })
                else:
                    articles.append({
                        "source": "User Source",
                        "title": txt_file.stem.replace("_", " ").replace("-", " ").title(),
                        "link": "",
                        "content": content[:3000],
                        "published": datetime.now().strftime("%d %B %Y"),
                        "pub_timestamp": datetime.now().timestamp(),
                        "from_user_sources": True
                    })
            except Exception as e:
                print(f"    ⚠️  Error reading {txt_file}: {e}")
        
        # Process JSON files
        for json_file in subfolder.glob("*.json"):
            try:
                data = json.loads(json_file.read_text(encoding='utf-8'))
                
                if isinstance(data, list):
                    for item in data:
                        articles.append({
                            "source": item.get("source", "User Source"),
                            "title": item.get("title", "Untitled"),
                            "link": item.get("link", item.get("url", "")),
                            "content": item.get("content", item.get("summary", item.get("text", "")))[:3000],
                            "published": item.get("published", datetime.now().strftime("%d %B %Y")),
                            "pub_timestamp": datetime.now().timestamp(),
                            "from_user_sources": True
                        })
                elif isinstance(data, dict):
                    articles.append({
                        "source": data.get("source", "User Source"),
                        "title": data.get("title", "Untitled"),
                        "link": data.get("link", data.get("url", "")),
                        "content": data.get("content", data.get("summary", data.get("text", "")))[:3000],
                        "published": data.get("published", datetime.now().strftime("%d %B %Y")),
                        "pub_timestamp": datetime.now().timestamp(),
                        "from_user_sources": True
                    })
            except Exception as e:
                print(f"    ⚠️  Error reading {json_file}: {e}")
        
        # Process Markdown files
        for md_file in subfolder.glob("*.md"):
            if md_file.name.lower() == 'readme.md':
                continue
            try:
                content = md_file.read_text(encoding='utf-8')
                title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
                title = title_match.group(1) if title_match else md_file.stem.replace("_", " ").title()
                
                articles.append({
                    "source": "User Source",
                    "title": title,
                    "link": "",
                    "content": content[:3000],
                    "published": datetime.now().strftime("%d %B %Y"),
                    "pub_timestamp": datetime.now().timestamp(),
                    "from_user_sources": True
                })
            except Exception as e:
                print(f"    ⚠️  Error reading {md_file}: {e}")
    
    print(f"  ✓ Loaded {len(articles)} user-provided sources")
    return articles


def generate_article_list(articles: list) -> str:
    """Generate a formatted list of all articles for review."""
    output = []
    output.append("=" * 70)
    output.append("FULL ARTICLE LIST FOR REVIEW")
    output.append(f"Total articles: {len(articles)}")
    output.append("=" * 70)
    output.append("")
    
    for i, article in enumerate(articles, 1):
        user_flag = " ⭐ [USER SOURCE]" if article.get('from_user_sources') else ""
        output.append(f"[{i}]{user_flag}")
        output.append(f"    Title: {article['title']}")
        output.append(f"    Source: {article['source']}")
        output.append(f"    Date: {article['published']}")
        output.append(f"    Link: {article['link'][:80]}..." if len(article.get('link', '')) > 80 else f"    Link: {article.get('link', 'N/A')}")
        output.append(f"    Preview: {article['content'][:150]}...")
        output.append("")
    
    output.append("=" * 70)
    output.append("To include/exclude specific articles, provide feedback like:")
    output.append("  - 'Include articles 3, 7, 12 in Market Signals'")
    output.append("  - 'Exclude article 5'")
    output.append("  - 'Article 8 should be in Deals section'")
    output.append("=" * 70)
    
    return "\n".join(output)


def generate_executive_summary(articles: list, sections_content: dict, api_key: str, recipient_name: str = "Reader") -> str:
    """Generate Axios-style executive summary."""
    
    client = Anthropic(api_key=api_key)
    
    # Prepare summary of selected articles
    selected_summary = ""
    for section_key, section_data in sections_content.items():
        if section_data.get("stories"):
            selected_summary += f"\n{section_data['title'].upper()}:\n"
            for story in section_data["stories"]:
                selected_summary += f"- {story['headline']}\n"
    
    prompt = f"""{EXECUTIVE_SUMMARY_PROMPT}

SELECTED ARTICLES FOR THIS NEWSLETTER:
{selected_summary}

RECIPIENT NAME: {recipient_name}

Generate the executive summary now. Start with "Good morning," (without the name - we'll add it separately).
Use proper markdown formatting with **bold** for headers."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    summary = response.content[0].text
    
    # Add greeting with name if not already there
    if not summary.strip().startswith("Good morning"):
        summary = f"**Good morning,**\n\n{summary}"
    
    return summary


def categorize_and_write_newsletter(
    articles: list, 
    api_key: Optional[str] = None,
    custom_instructions: Optional[str] = None,
    stories_per_section: int = 3,
    include_articles: Optional[List[int]] = None,
    exclude_articles: Optional[List[int]] = None
) -> dict:
    """Use Claude to categorize articles and write newsletter sections in Axios style."""
    
    if not api_key:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
    
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found.")
    
    if not custom_instructions:
        custom_instructions = os.environ.get("EXTRA_PROMPT", "")
    
    client = Anthropic(api_key=api_key)
    
    # Filter articles if specified
    if exclude_articles:
        articles = [a for i, a in enumerate(articles) if (i+1) not in exclude_articles]
    
    # Prepare articles for Claude
    articles_text = ""
    for i, article in enumerate(articles[:60]):
        user_flag = " [USER-PROVIDED SOURCE - PRIORITIZE]" if article.get('from_user_sources') else ""
        include_flag = " [EDITOR REQUESTED INCLUSION]" if include_articles and (i+1) in include_articles else ""
        articles_text += f"""
---
[Article {i+1}]{user_flag}{include_flag}
Source: {article['source']}
Title: {article['title']}
Published: {article['published']}
Link: {article['link']}
Content: {article['content'][:1000]}
---
"""
    
    sections_desc = ""
    for key, section in SECTIONS.items():
        sub_theme_note = ""
        if section.get("sub_themes"):
            sub_theme_note = f"\n- Sub-themes (MUST tag each story): {', '.join(section['sub_themes'])}"
        sections_desc += f"""
{section['title'].upper()}:
- {section['description']}{sub_theme_note}
- Focus: {section['prompt_focus']}
"""

    prompt = f"""You are the editor of The Second Curves Media & Events Brief, a board-level intelligence newsletter.

{WRITING_STYLE}

YOUR TASK:
Analyze articles and write a newsletter with three sections in AXIOS STYLE.

SECTIONS:
{sections_desc}

RULES:
1. USER-PROVIDED SOURCES and EDITOR REQUESTED articles get priority
2. Each section: {stories_per_section} stories (if enough quality content)
3. NO "In Brief" items - only main stories
4. Write in Axios bullet-point style with "Why it matters:", "The details:", "What to watch:"
5. For MARKET SIGNALS: tag each story with "Macro Economy" or "Consumer Trends"

{f"EDITORIAL INSTRUCTIONS: {custom_instructions}" if custom_instructions else ""}

ARTICLES:
{articles_text}

Return JSON:
{{
    "sections": {{
        "market_signals": {{
            "stories": [
                {{
                    "article_index": 1,
                    "headline": "Clear, punchy headline",
                    "summary": "<span class='label'>Why it matters:</span><ul><li>Key strategic point</li></ul><span class='label'>The details:</span><ul><li>Fact 1</li><li>Fact 2</li></ul><span class='label'>What to watch:</span><ul><li>Forward implication</li></ul>",
                    "sub_theme": "Macro Economy"
                }}
            ]
        }},
        "deals": {{
            "stories": [...]
        }},
        "hires_fires": {{
            "stories": [...]
        }}
    }}
}}

CRITICAL: 
- summary must use HTML with <span class='label'> and <ul><li> tags
- market_signals stories MUST have sub_theme ("Macro Economy" or "Consumer Trends")
- Return ONLY valid JSON"""

    print("  Writing newsletter with Claude (Axios style)...")
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=6000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    response_text = response.content[0].text
    
    try:
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = json.loads(response_text)
    except json.JSONDecodeError as e:
        print(f"  ⚠️  JSON parse error: {e}")
        raise
    
    # Enrich stories
    enriched_sections = {}
    
    for section_key, section_config in SECTIONS.items():
        section_data = result.get("sections", {}).get(section_key, {})
        
        enriched_stories = []
        for story in section_data.get("stories", []):
            idx = story.get("article_index", 1) - 1
            if 0 <= idx < len(articles):
                original = articles[idx]
                enriched_story = {
                    "headline": story.get("headline", original["title"]),
                    "summary": story.get("summary", original["content"]),
                    "source": original["source"],
                    "link": original["link"],
                    "published": original["published"]
                }
                if story.get("sub_theme"):
                    enriched_story["sub_theme"] = story.get("sub_theme")
                enriched_stories.append(enriched_story)
        
        enriched_sections[section_key] = {
            "title": section_config["title"],
            "icon": section_config["icon"],
            "stories": enriched_stories,
            "sub_themes": section_config.get("sub_themes")
        }
    
    return {
        "sections": enriched_sections
    }


def render_newsletter(
    content: dict, 
    output_format: str = "html",
    title: str = "The Second Curves Media & Events Brief",
    footer_text: str = None,
    executive_summary: str = None,
    logo_url: str = None
) -> str:
    """Render the newsletter content to HTML or Markdown."""
    from jinja2 import Template
    
    template_str = HTML_TEMPLATE if output_format == "html" else MARKDOWN_TEMPLATE
    template = Template(template_str)
    
    return template.render(
        title=title,
        date=datetime.now().strftime("%d %B %Y"),
        executive_summary=executive_summary,
        sections=content.get("sections", {}),
        footer_text=footer_text,
        logo_url=logo_url
    )


def generate_newsletter(
    days_back: int = 7,
    stories_per_section: int = 3,
    output_format: str = "html",
    title: str = "The Second Curves Media & Events Brief",
    api_key: Optional[str] = None,
    custom_feeds: Optional[dict] = None,
    sources_folder: Optional[str] = None,
    footer_text: Optional[str] = None,
    recipient_name: str = "Reader",
    list_articles_only: bool = False,
    include_articles: Optional[List[int]] = None,
    exclude_articles: Optional[List[int]] = None,
    logo_url: Optional[str] = None
) -> str:
    """Main function to generate a complete newsletter."""
    
    if not api_key:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
    
    feeds = custom_feeds or RSS_FEEDS
    
    print("\n" + "=" * 60)
    print("📰 THE SECOND CURVES MEDIA & EVENTS BRIEF")
    print("=" * 60)
    
    # Step 1: Fetch RSS articles
    print(f"\n[1/5] Fetching articles from {len(feeds)} RSS sources...")
    articles = fetch_feeds(feeds, days_back)
    
    # Step 2: Load user sources
    if sources_folder:
        print(f"\n[2/5] Loading user-provided sources...")
        user_articles = load_user_sources(sources_folder)
        articles = user_articles + articles
    else:
        print(f"\n[2/5] No user sources folder specified...")
    
    print(f"\n  Total articles: {len(articles)}")
    
    if not articles:
        return "No articles found."
    
    # If list-only mode, return article list
    if list_articles_only:
        return generate_article_list(articles)
    
    # Step 3: Write newsletter
    print(f"\n[3/5] Writing newsletter (Axios style)...")
    content = categorize_and_write_newsletter(
        articles, 
        api_key,
        stories_per_section=stories_per_section,
        include_articles=include_articles,
        exclude_articles=exclude_articles
    )
    
    # Step 4: Generate executive summary
    print(f"\n[4/5] Generating executive summary...")
    exec_summary = generate_executive_summary(
        articles, 
        content["sections"], 
        api_key,
        recipient_name
    )
    
    # Step 5: Render
    print(f"\n[5/5] Rendering {output_format.upper()}...")
    newsletter = render_newsletter(
        content, 
        output_format, 
        title, 
        footer_text,
        exec_summary,
        logo_url
    )
    
    total_stories = sum(len(s.get("stories", [])) for s in content["sections"].values())
    print(f"  ✓ Generated {total_stories} stories + executive summary")
    
    print("\n" + "=" * 60)
    print("✅ DONE!")
    print("=" * 60 + "\n")
    
    return newsletter


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate The Second Curves Media & Events Brief"
    )
    
    parser.add_argument("--output", "-o", choices=["html", "markdown", "md"], default="html")
    parser.add_argument("--days", "-d", type=int, default=7)
    parser.add_argument("--stories", "-s", type=int, default=3)
    parser.add_argument("--title", "-t", default="The Second Curves Media & Events Brief")
    parser.add_argument("--sources-folder", help="Path to sources folder")
    parser.add_argument("--out-file", "-f", help="Output file path")
    parser.add_argument("--api-key", help="Anthropic API key")
    parser.add_argument("--footer", default="Published by Second Curve Consulting")
    parser.add_argument("--recipient", default="Reader", help="Recipient name for greeting")
    parser.add_argument("--list-articles", action="store_true", help="List all articles for review (no newsletter)")
    parser.add_argument("--include", type=str, help="Article numbers to include (comma-separated)")
    parser.add_argument("--exclude", type=str, help="Article numbers to exclude (comma-separated)")
    parser.add_argument("--logo", type=str, help="URL to logo image (or path if using assets folder)")
    
    args = parser.parse_args()
    
    include_articles = [int(x.strip()) for x in args.include.split(",")] if args.include else None
    exclude_articles = [int(x.strip()) for x in args.exclude.split(",")] if args.exclude else None
    
    output_format = "markdown" if args.output == "md" else args.output
    
    try:
        result = generate_newsletter(
            days_back=args.days,
            stories_per_section=args.stories,
            output_format=output_format,
            title=args.title,
            api_key=args.api_key,
            sources_folder=args.sources_folder,
            footer_text=args.footer,
            recipient_name=args.recipient,
            list_articles_only=args.list_articles,
            include_articles=include_articles,
            exclude_articles=exclude_articles,
            logo_url=args.logo
        )
        
        if args.out_file:
            with open(args.out_file, "w", encoding="utf-8") as f:
                f.write(result)
            print(f"📄 Saved to: {args.out_file}")
        else:
            print(result)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
