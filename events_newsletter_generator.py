#!/usr/bin/env python3
"""
B2B Trade Press & Events Industry Newsletter Generator
-------------------------------------------------------
A specialized newsletter for the global trade press, conference,
and tradeshow market. Written in FT/Economist style for board-level readers.

Sections:
1. Market Signals - Strategic trends, market movements, analysis
2. Deals (M&A) - Mergers, acquisitions, investments, divestitures
3. Hires & Fires - Executive appointments, departures, restructuring

Usage:
    python events_newsletter_generator.py
    python events_newsletter_generator.py --sources-folder ./my_sources
    python events_newsletter_generator.py --output html --out-file newsletter.html

Requirements:
    pip install anthropic feedparser requests python-dateutil jinja2 beautifulsoup4
"""

import argparse
import json
import os
import re
from pathlib import Path
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from typing import Optional, List, Dict, Any

import feedparser
import requests
from anthropic import Anthropic

# =============================================================================
# CONFIGURATION
# =============================================================================

# Industry-specific RSS feeds for trade press, events, and exhibitions
RSS_FEEDS = {
    # Exhibition & Events Industry
    "exhibition_world": "https://www.exhibitionworld.co.uk/feed",
    "exhibition_news": "https://www.exhibitionnews.co.uk/feed",
    "mash_media": "https://www.mashmedia.net/feed/",
    "conference_news": "https://www.conference-news.co.uk/feed",
    "access_aa": "https://accessaa.co.uk/feed/",
    "eventindustrynews": "https://www.eventindustrynews.com/feed",
    "tsnn": "https://www.tsnn.com/feed",  # Trade Show News Network
    "exhibitor_online": "https://www.exhibitoronline.com/news/rss.xml",

    # B2B Media & Publishing
    "fipp": "https://www.fipp.com/feed/",  # Media industry
    "inpublishing": "https://www.inpublishing.co.uk/feed",
    "pressgazette": "https://pressgazette.co.uk/feed/",
    "journalism_co_uk": "https://www.journalism.co.uk/feed/",

    # Business News (filtered for media/events M&A)
    "pe_hub_media": "https://www.pehub.com/feed/",

    # Marketing & Events Adjacent
    "event_marketer": "https://www.eventmarketer.com/feed/",
    "bizbash": "https://www.bizbash.com/rss.xml",
    "skift_meetings": "https://skift.com/meetings/feed/",
}

# Writing style configuration
WRITING_STYLE = """
WRITING STYLE - FT/ECONOMIST EDITORIAL STANDARDS:

TONE:
- Authoritative and analytical, never promotional
- Assume reader is a senior executive or board member
- Focus on strategic implications, not just facts
- Use measured, confident language - avoid hyperbole
- Be direct and concise - every sentence must earn its place

STRUCTURE:
- Lead with the strategic significance ("why this matters")
- Follow with the key facts
- Close with forward-looking implications
- Use short paragraphs (2-3 sentences max)

LANGUAGE:
- Prefer active voice
- Avoid jargon unless industry-standard
- No exclamation marks
- No marketing speak ("excited to announce", "thrilled", "game-changing")
- Use precise numbers and attribution
- "Sources suggest" or "according to" for unconfirmed information

ANALYSIS:
- Connect individual stories to broader market trends
- Reference comparable deals/moves where relevant
- Note what isn't being said as well as what is
- Consider competitive implications

EXAMPLES OF GOOD PHRASING:
- "The acquisition signals..." not "This is a game-changing deal"
- "The move comes amid..." not "In exciting news..."
- "Industry observers note..." not "Everyone is talking about..."
- "The appointment suggests a strategic shift toward..." not "Great hire!"
"""

# =============================================================================
# BOARD-LEVEL FILTERING & PRIORITISATION (Stage 1)
# =============================================================================

FILTERING_SPEC = """
AI BRIEF: ARTICLE FILTERING & PRIORITISATION (BOARD-LEVEL)

Role:
- You are a senior industry intelligence analyst.
Audience:
- PE investors, board directors, CEOs, corp dev leaders in global B2B media & live events.

Objective:
- Filter and prioritise only articles that reveal structural change or economically meaningful shifts.
- Focus on implications for capital allocation, valuation, strategy, revenue quality, margins, or risk.
Exclude:
- Product launches, vendor marketing, event-tech hype, tactical “how-to”, generic macro with no industry transmission.

Core Analytical Lenses (article must fit at least one):
1) Macro & Capital
2) Formats & Attention
3) Geography & Exposure
4) Pricing, Yield & Revenue Quality
5) Portfolio Strategy & M&A
6) Cost Structure & Operating Leverage

Mandatory questions:
- What is the signal?
- Why does this matter economically?
- Who is affected?
- Structural or cyclical?
- What board-level question does it raise?

Scoring (/25): 0–5 each:
- Strategic relevance
- Economic impact
- Decision usefulness
- Signal strength
- Transferability

Interpretation:
- 20–25 Must include
- 14–19 Include if space allows
- <14 Exclude
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
        "prompt_focus": (
            "Focus on strategic market movements, industry trends, new ventures, partnerships, "
            "venue developments, format innovations, and market analysis. IMPORTANT: Organize "
            "stories under two sub-themes: (1) MACRO ECONOMY - economic conditions affecting the "
            "industry like recession fears, interest rates, corporate spending trends, and "
            "(2) CONSUMER TRENDS - attendee behavior, visitor patterns, audience preferences, "
            "and demand shifts. Label each story with its sub-theme."
        )
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
        "prompt_focus": (
            "Focus on M&A activity, private equity moves, strategic investments, and divestitures. "
            "Include deal values where known, and analyze strategic rationale and market implications."
        )
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
        "prompt_focus": (
            "Focus on senior executive movements (C-suite, MD, VP level and above). "
            "Analyze what appointments signal about company strategy. Note patterns in hiring "
            "(e.g., digital expertise, international expansion)."
        )
    }
}

# HTML Template - Clean, professional, FT-style
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
            font-family: 'Georgia', 'Times New Roman', serif;
            max-width: 700px;
            margin: 0 auto;
            padding: 20px;
            background: #FFF9F5;
            color: #1a1a1a;
            line-height: 1.7;
            font-size: 17px;
        }
        .header {
            border-bottom: 3px double #1a1a1a;
            padding-bottom: 20px;
            margin-bottom: 30px;
            text-align: center;
        }
        .header h1 {
            font-size: 32px;
            font-weight: 700;
            margin: 0 0 5px 0;
            letter-spacing: -0.5px;
        }
        .header .tagline {
            font-style: italic;
            color: #666;
            font-size: 14px;
            margin-bottom: 10px;
        }
        .header .date {
            font-size: 13px;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .intro {
            font-size: 18px;
            font-style: italic;
            color: #444;
            border-left: 3px solid #c41e3a;
            padding-left: 20px;
            margin: 30px 0;
        }
        .section {
            margin-bottom: 40px;
        }
        .section-header {
            display: flex;
            align-items: center;
            border-bottom: 1px solid #ccc;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        .section-header h2 {
            font-size: 22px;
            font-weight: 700;
            margin: 0;
            color: #1a1a1a;
        }
        .section-header .icon {
            font-size: 20px;
            margin-right: 10px;
        }
        .sub-theme {
            font-size: 16px;
            font-weight: 700;
            color: #c41e3a;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin: 25px 0 15px 0;
            padding-bottom: 5px;
            border-bottom: 1px dotted #c41e3a;
        }
        .story {
            margin-bottom: 25px;
            padding-bottom: 25px;
            border-bottom: 1px dotted #ddd;
        }
        .story:last-child {
            border-bottom: none;
        }
        .story h3 {
            font-size: 19px;
            font-weight: 700;
            margin: 0 0 10px 0;
            line-height: 1.3;
        }
        .story .meta {
            font-size: 12px;
            color: #888;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .story .content {
            color: #333;
        }
        .story .content p {
            margin: 0 0 12px 0;
        }
        .story .source-link {
            font-size: 13px;
            color: #c41e3a;
            text-decoration: none;
        }
        .story .source-link:hover {
            text-decoration: underline;
        }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ccc;
            text-align: center;
            font-size: 12px;
            color: #888;
        }
        .no-stories {
            color: #888;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ title }}</h1>
        <div class="tagline">Intelligence for the global exhibitions, events & trade media industry</div>
        <div class="date">{{ date }}</div>
    </div>

    {% if intro %}
    <div class="intro">
        {{ intro }}
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
                    <div class="content">
                        {{ story.summary }}
                    </div>
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
                    <div class="content">
                        {{ story.summary }}
                    </div>
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
        {{ footer_text | default('Published by Second Curves') }}
    </div>
</body>
</html>
"""

# Markdown Template
MARKDOWN_TEMPLATE = """# {{ title }}

*Intelligence for the global exhibitions, events & trade media industry*

**{{ date }}**

---

{% if intro %}
> {{ intro }}

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
            except Exception:
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
                        except Exception:
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

    for txt_file in folder.glob("*.txt"):
        try:
            content = txt_file.read_text(encoding='utf-8')

            lines = content.strip().split('\n')
            if all(line.strip().startswith(('http://', 'https://')) for line in lines if line.strip()):
                for url in lines:
                    url = url.strip()
                    if url:
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

    for json_file in folder.glob("*.json"):
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

    for md_file in folder.glob("*.md"):
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


def filter_and_score_articles(
    articles: list,
    api_key: Optional[str] = None,
    custom_instructions: Optional[str] = None,
    max_articles_in_prompt: int = 60
) -> List[Dict[str, Any]]:
    """
    Stage 1: Filter + score articles using FILTERING_SPEC.
    Returns a ranked shortlist enriched with original article metadata.
    """

    if not api_key:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found.")

    if not custom_instructions:
        custom_instructions = os.environ.get("EXTRA_PROMPT", "")

    client = Anthropic(api_key=api_key)

    articles_text = ""
    for i, article in enumerate(articles[:max_articles_in_prompt]):
        user_flag = " [USER-PROVIDED SOURCE - PRIORITIZE]" if article.get('from_user_sources') else ""
        articles_text += f"""
---
[Article {i+1}]{user_flag}
Source: {article['source']}
Title: {article['title']}
Published: {article['published']}
Link: {article['link']}
Content: {article['content'][:900]}
---
"""

    prompt = f"""You are the research desk for a board-level intelligence newsletter in global B2B media & live events.

{FILTERING_SPEC}

{f"SPECIAL EDITORIAL INSTRUCTIONS: {custom_instructions}" if custom_instructions else ""}

ARTICLES:
{articles_text}

TASK:
1) Exclude anything that does not meet the inclusion criteria.
2) For each INCLUDED article:
   - Assign ONE primary lens from the six.
   - Write why_it_matters (2–3 sentences; implications only, not a summary).
   - Write board_question (1 sentence).
   - Score each dimension 0–5 and provide total /25.
3) Rank included articles by:
   - total_score desc,
   - then user_provided first,
   - then recency.

OUTPUT:
Return ONLY valid JSON in exactly this structure:
{{
  "included": [
    {{
      "article_index": 1,
      "primary_lens": "Pricing, Yield & Revenue Quality",
      "why_it_matters": "...",
      "board_question": "...",
      "scores": {{
        "strategic_relevance": 0,
        "economic_impact": 0,
        "decision_usefulness": 0,
        "signal_strength": 0,
        "transferability": 0,
        "total": 0
      }},
      "include_tier": "must_include|space_allows",
      "notes": "Optional: 1 short sentence on what to watch next"
    }}
  ]
}}

Rules:
- Do not invent facts not present in the article snippet.
- If unsure, state assumptions briefly in notes.
- Aim for 8–20 included items if available; otherwise include fewer.
"""

    print("  Stage 1: Filtering and scoring articles (board-level lens)...")

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4500,
        messages=[{"role": "user", "content": prompt}]
    )

    response_text = response.content[0].text

    try:
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        result = json.loads(json_match.group() if json_match else response_text)
    except json.JSONDecodeError as e:
        print(f"  ⚠️  JSON parse error (Stage 1): {e}")
        print(f"  Response preview: {response_text[:500]}")
        raise

    included = result.get("included", [])

    enriched: List[Dict[str, Any]] = []
    for item in included:
        idx = int(item.get("article_index", 1)) - 1
        if 0 <= idx < len(articles):
            a = articles[idx]
            scores = item.get("scores", {})
            enriched.append({
                **item,
                "title": a.get("title", ""),
                "source": a.get("source", ""),
                "link": a.get("link", ""),
                "published": a.get("published", ""),
                "pub_timestamp": a.get("pub_timestamp", 0),
                "from_user_sources": a.get("from_user_sources", False),
                "total_score": int(scores.get("total", 0)),
            })

    enriched.sort(
        key=lambda x: (
            -x.get("total_score", 0),
            0 if x.get("from_user_sources") else 1,
            -x.get("pub_timestamp", 0),
        )
    )

    print(f"  ✓ Stage 1 shortlisted {len(enriched)} articles")
    return enriched


def categorize_and_write_newsletter(
    shortlisted: list,
    api_key: Optional[str] = None,
    custom_instructions: Optional[str] = None,
    stories_per_section: int = 3
) -> dict:
    """Stage 2: Use Claude to write newsletter sections from a shortlisted set."""

    if not api_key:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found.")

    if not custom_instructions:
        custom_instructions = os.environ.get("EXTRA_PROMPT", "")

    client = Anthropic(api_key=api_key)

    # Prepare shortlisted items for Claude (include lens + scores for prioritisation)
    articles_text = ""
    for i, article in enumerate(shortlisted[:30]):
        user_flag = " [USER-PROVIDED SOURCE - PRIORITIZE]" if article.get('from_user_sources') else ""
        articles_text += f"""
---
[Shortlist {i+1}]{user_flag}
Source: {article.get('source', '')}
Title: {article.get('title', 'Untitled')}
Published: {article.get('published', '')}
Link: {article.get('link', '')}
PrimaryLens: {article.get('primary_lens', '')}
ScoreTotal: {article.get('total_score', '')}/25
WhyItMatters: {article.get('why_it_matters', '')}
BoardQuestion: {article.get('board_question', '')}
---
"""

    sections_desc = ""
    for _, section in SECTIONS.items():
        sections_desc += f"""
{section['title'].upper()}:
- {section['description']}
- Focus: {section['prompt_focus']}
"""

    prompt = f"""You are the editor of a prestigious industry intelligence newsletter covering the global B2B trade press, conferences, exhibitions, and events industry. Your readers are C-suite executives, board members, investors, and senior strategists.

{WRITING_STYLE}

YOUR TASK:
Using ONLY the shortlisted items, produce a newsletter with three sections. For each section, select the most significant stories and write them in FT/Economist editorial style.

SECTIONS TO PRODUCE:
{sections_desc}

IMPORTANT RULES:
1. USER-PROVIDED SOURCES (marked with [USER-PROVIDED SOURCE]) should be prioritized - the editor specifically collected these
2. Each section should have {stories_per_section} main stories (if enough quality content exists)
3. If a story doesn't clearly fit a section, use your judgment or skip it
4. Avoid duplicating the same story across sections
5. Write headlines that are informative, not clickbait
6. Summaries should be 2-3 short paragraphs analyzing the strategic significance

{f"SPECIAL EDITORIAL INSTRUCTIONS: {custom_instructions}" if custom_instructions else ""}

SHORTLISTED ITEMS TO ANALYZE:
{articles_text}

Respond with valid JSON in this exact structure:
{{
    "intro": "A 2-3 sentence editorial overview of this period's key themes and what they signal for the industry",
    "sections": {{
        "market_signals": {{
            "stories": [
                {{
                    "shortlist_index": 1,
                    "headline": "Strategic, informative headline",
                    "summary": "2-3 paragraph analysis in FT style. Focus on strategic implications.",
                    "sub_theme": "Macro Economy",
                    "why_selected": "Brief editorial note on significance"
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

IMPORTANT: For market_signals stories, you MUST include "sub_theme" field with either "Macro Economy" or "Consumer Trends".
Do NOT include any "briefs" or "in brief" items - only main stories.
If a section has no relevant stories, use empty arrays.
Return ONLY valid JSON, no other text."""

    print("  Asking Claude to analyze and write newsletter (from shortlist)...")

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=6000,
        messages=[{"role": "user", "content": prompt}]
    )

    response_text = response.content[0].text

    try:
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        result = json.loads(json_match.group() if json_match else response_text)
    except json.JSONDecodeError as e:
        print(f"  ⚠️  JSON parse error: {e}")
        print(f"  Response preview: {response_text[:500]}")
        raise

    enriched_sections = {}

    for section_key, section_config in SECTIONS.items():
        section_data = result.get("sections", {}).get(section_key, {})

        enriched_stories = []
        for story in section_data.get("stories", []):
            idx = int(story.get("shortlist_index", 1)) - 1
            if 0 <= idx < len(shortlisted):
                original = shortlisted[idx]
                enriched_story = {
                    "headline": story.get("headline", original.get("title", "")),
                    "summary": story.get("summary", ""),
                    "source": original.get("source", ""),
                    "link": original.get("link", ""),
                    "published": original.get("published", "")
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
        "intro": result.get("intro", ""),
        "sections": enriched_sections
    }


def render_newsletter(
    content: dict,
    output_format: str = "html",
    title: str = "Events Industry Intelligence",
    footer_text: str = None
) -> str:
    """Render the newsletter content to HTML or Markdown."""
    from jinja2 import Template

    template_str = HTML_TEMPLATE if output_format == "html" else MARKDOWN_TEMPLATE
    template = Template(template_str)

    return template.render(
        title=title,
        date=datetime.now().strftime("%d %B %Y"),
        intro=content.get("intro", ""),
        sections=content.get("sections", {}),
        footer_text=footer_text
    )


def generate_newsletter(
    days_back: int = 7,
    stories_per_section: int = 3,
    output_format: str = "html",
    title: str = "The Second Curves Media & Events Brief",
    api_key: Optional[str] = None,
    custom_feeds: Optional[dict] = None,
    sources_folder: Optional[str] = None,
    footer_text: Optional[str] = None
) -> str:
    """Main function to generate a complete newsletter."""

    feeds = custom_feeds or RSS_FEEDS

    print("\n" + "=" * 60)
    print("📰 B2B TRADE PRESS & EVENTS NEWSLETTER GENERATOR")
    print("=" * 60)

    # Step 1: Fetch RSS articles
    print(f"\n[1/5] Fetching articles from {len(feeds)} RSS sources...")
    articles = fetch_feeds(feeds, days_back)

    # Step 2: Load user sources
    if sources_folder:
        print(f"\n[2/5] Loading user-provided sources...")
        user_articles = load_user_sources(sources_folder)
        articles = user_articles + articles  # Prioritize user sources
    else:
        print(f"\n[2/5] No user sources folder specified, skipping...")

    print(f"\n  Total articles to analyze: {len(articles)}")

    if not articles:
        return "No articles found. Check RSS feeds and sources folder."

    # Step 3: Filter + score (board-level)
    print(f"\n[3/5] Filtering + scoring articles (board-level lens)...")
    shortlist = filter_and_score_articles(articles, api_key=api_key)

    if not shortlist:
        return "No articles passed the board-level filter this period."

    # Step 4: Write newsletter from shortlist
    print(f"\n[4/5] Writing newsletter with Claude from shortlist...")
    content = categorize_and_write_newsletter(
        shortlist,
        api_key,
        stories_per_section=stories_per_section
    )

    total_stories = sum(len(s.get("stories", [])) for s in content["sections"].values())
    print(f"  ✓ Generated {total_stories} main stories")

    # Step 5: Render
    print(f"\n[5/5] Rendering {output_format.upper()} newsletter...")
    newsletter = render_newsletter(content, output_format, title, footer_text)
    print(f"  ✓ Newsletter complete ({len(newsletter):,} characters)")

    print("\n" + "=" * 60)
    print("✅ DONE!")
    print("=" * 60 + "\n")

    return newsletter


# =============================================================================
# CLI INTERFACE
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate a B2B Trade Press & Events industry newsletter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python events_newsletter_generator.py
  python events_newsletter_generator.py --sources-folder ./my_sources
  python events_newsletter_generator.py --days 14 --stories 4 --output html

Sources Folder:
  Create a folder with your own sources in these formats:
  - .txt files with URLs (one per line)
  - .txt files with article text
  - .json files with article data: {"title": "...", "content": "...", "source": "..."}
  - .md files with content

Environment Variables:
  ANTHROPIC_API_KEY - Your Anthropic API key (required)
  EXTRA_PROMPT - Extra editorial instructions (optional)
        """
    )

    parser.add_argument("--output", "-o", choices=["html", "markdown", "md"], default="html",
                        help="Output format (default: html)")
    parser.add_argument("--days", "-d", type=int, default=7,
                        help="How many days back to look for articles (default: 7)")
    parser.add_argument("--stories", "-s", type=int, default=3,
                        help="Number of main stories per section (default: 3)")
    parser.add_argument("--title", "-t", default="The Second Curves Media & Events Brief",
                        help="Newsletter title")
    parser.add_argument("--sources-folder", help="Path to folder containing your collected sources")
    parser.add_argument("--out-file", "-f", help="Output file path (default: prints to stdout)")
    parser.add_argument("--api-key", help="Anthropic API key (or set ANTHROPIC_API_KEY env var)")
    parser.add_argument("--footer", default="Published by Events Industry Intelligence",
                        help="Footer text for the newsletter")

    args = parser.parse_args()
    output_format = "markdown" if args.output == "md" else args.output

    try:
        newsletter = generate_newsletter(
            days_back=args.days,
            stories_per_section=args.stories,
            output_format=output_format,
            title=args.title,
            api_key=args.api_key,
            sources_folder=args.sources_folder,
            footer_text=args.footer
        )

        if args.out_file:
            with open(args.out_file, "w", encoding="utf-8") as f:
                f.write(newsletter)
            print(f"📄 Saved to: {args.out_file}")
        else:
            print("\n" + "=" * 60)
            print("NEWSLETTER OUTPUT:")
            print("=" * 60 + "\n")
            print(newsletter)

    except ValueError as e:
        print(f"\n❌ Error: {e}")
        raise
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        raise


if __name__ == "__main__":
    main()
