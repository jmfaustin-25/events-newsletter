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
    "pe_hub_media": "https://www.pehub.com/feed/",  # Private equity deals
    
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
        "prompt_focus": "Focus on strategic market movements, industry trends, new ventures, partnerships, venue developments, format innovations, and market analysis. IMPORTANT: Organize stories under two sub-themes: (1) MACRO ECONOMY - economic conditions affecting the industry like recession fears, interest rates, corporate spending trends, and (2) CONSUMER TRENDS - attendee behavior, visitor patterns, audience preferences, and demand shifts. Label each story with its sub-theme."
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
        "prompt_focus": "Focus on M&A activity, private equity moves, strategic investments, and divestitures. Include deal values where known, and analyze strategic rationale and market implications."
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
        "prompt_focus": "Focus on senior executive movements (C-suite, MD, VP level and above). Analyze what appointments signal about company strategy. Note patterns in hiring (e.g., digital expertise, international expansion)."
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
            
            # Add headers to avoid blocks
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            # Some feeds need direct request
            try:
                response = requests.get(feed_url, headers=headers, timeout=15)
                feed = feedparser.parse(response.content)
            except:
                feed = feedparser.parse(feed_url)
            
            if not feed.entries:
                print(f"    ⚠️  No entries found")
                continue
                
            for entry in feed.entries[:15]:  # Limit per source
                # Parse publication date
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
                
                # Skip old articles
                if pub_date < cutoff_date:
                    continue
                
                # Extract content
                content = ""
                if hasattr(entry, 'summary'):
                    content = entry.summary
                elif hasattr(entry, 'description'):
                    content = entry.description
                elif hasattr(entry, 'content'):
                    content = entry.content[0].value if entry.content else ""
                
                # Clean HTML from content
                content = re.sub(r'<[^>]+>', '', content)
                content = re.sub(r'\s+', ' ', content).strip()
                content = content[:2000]  # Truncate
                
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
    
    # Sort by date (newest first)
    articles.sort(key=lambda x: x['pub_timestamp'], reverse=True)
    print(f"  ✓ Fetched {len(articles)} articles from RSS feeds")
    return articles


def load_user_sources(sources_folder: str) -> list:
    """Load articles from user-provided sources folder.
    
    Supports:
    - .txt files with URLs (one per line)
    - .txt files with article text
    - .json files with article data
    - .md files with content
    """
    articles = []
    folder = Path(sources_folder)
    
    if not folder.exists():
        print(f"  Sources folder not found: {sources_folder}")
        return articles
    
    print(f"  Loading user sources from {sources_folder}...")
    
    # Process text files
    for txt_file in folder.glob("*.txt"):
        try:
            content = txt_file.read_text(encoding='utf-8')
            
            # Check if it's a URL list
            lines = content.strip().split('\n')
            if all(line.strip().startswith(('http://', 'https://')) for line in lines if line.strip()):
                # It's a URL list - we'll just note them for now
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
                # It's article content
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
    for json_file in folder.glob("*.json"):
        try:
            data = json.loads(json_file.read_text(encoding='utf-8'))
            
            # Handle array of articles
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
            # Handle single article object
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
    for md_file in folder.glob("*.md"):
        try:
            content = md_file.read_text(encoding='utf-8')
            # Try to extract title from first heading
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


def categorize_and_write_newsletter(
    articles: list, 
    api_key: Optional[str] = None,
    custom_instructions: Optional[str] = None,
    stories_per_section: int = 3
) -> dict:
    """Use Claude to categorize articles and write newsletter sections."""
    
    if not api_key:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
    
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found.")
    
    # Check for custom instructions from environment
    if not custom_instructions:
        custom_instructions = os.environ.get("EXTRA_PROMPT", "")
    
    client = Anthropic(api_key=api_key)
    
    # Prepare articles for Claude
    articles_text = ""
    for i, article in enumerate(articles[:60]):  # Limit to prevent token overflow
        user_flag = " [USER-PROVIDED SOURCE - PRIORITIZE]" if article.get('from_user_sources') else ""
        articles_text += f"""
---
[Article {i+1}]{user_flag}
Source: {article['source']}
Title: {article['title']}
Published: {article['published']}
Link: {article['link']}
Content: {article['content'][:1000]}
---
"""
    
    # Build section descriptions for prompt
    sections_desc = ""
    for key, section in SECTIONS.items():
        sections_desc += f"""
{section['title'].upper()}:
- {section['description']}
- Keywords: {', '.join(section['keywords'][:10])}
- Focus: {section['prompt_focus']}
"""

    prompt = f"""You are the editor of a prestigious industry intelligence newsletter covering the global B2B trade press, conferences, exhibitions, and events industry. Your readers are C-suite executives, board members, investors, and senior strategists.

{WRITING_STYLE}

YOUR TASK:
Analyze the provided articles and produce a newsletter with three sections. For each section, select the most significant stories and write them in FT/Economist editorial style.

SECTIONS TO PRODUCE:
{sections_desc}

IMPORTANT RULES:
1. USER-PROVIDED SOURCES (marked with [USER-PROVIDED SOURCE]) should be prioritized - the editor specifically collected these
2. Each section should have {stories_per_section} main stories (if enough quality content exists)
3. Include 2-4 "In Brief" items per section for lesser stories worth noting
4. If a story doesn't clearly fit a section, use your judgment or skip it
5. Avoid duplicating the same story across sections
6. Write headlines that are informative, not clickbait
7. Summaries should be 2-3 short paragraphs analyzing the strategic significance

{f"SPECIAL EDITORIAL INSTRUCTIONS: {custom_instructions}" if custom_instructions else ""}

ARTICLES TO ANALYZE:
{articles_text}

Respond with valid JSON in this exact structure:
{{
    "intro": "A 2-3 sentence editorial overview of this period's key themes and what they signal for the industry",
    "sections": {{
        "market_signals": {{
            "stories": [
                {{
                    "article_index": 1,
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

    print("  Asking Claude to analyze and write newsletter...")
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=6000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    response_text = response.content[0].text
    
    # Parse JSON response
    try:
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = json.loads(response_text)
    except json.JSONDecodeError as e:
        print(f"  ⚠️  JSON parse error: {e}")
        print(f"  Response preview: {response_text[:500]}")
        raise
    
    # Enrich stories with original article data
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
                # Add sub_theme if present (for market_signals)
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
    print(f"\n[1/4] Fetching articles from {len(feeds)} RSS sources...")
    articles = fetch_feeds(feeds, days_back)
    
    # Step 2: Load user sources
    if sources_folder:
        print(f"\n[2/4] Loading user-provided sources...")
        user_articles = load_user_sources(sources_folder)
        articles = user_articles + articles  # Prioritize user sources
    else:
        print(f"\n[2/4] No user sources folder specified, skipping...")
    
    print(f"\n  Total articles to analyze: {len(articles)}")
    
    if not articles:
        return "No articles found. Check RSS feeds and sources folder."
    
    # Step 3: Categorize and write with Claude
    print(f"\n[3/4] Writing newsletter with Claude...")
    content = categorize_and_write_newsletter(
        articles, 
        api_key,
        stories_per_section=stories_per_section
    )
    
    # Count stories
    total_stories = sum(len(s.get("stories", [])) for s in content["sections"].values())
    total_briefs = sum(len(s.get("briefs", [])) for s in content["sections"].values())
    print(f"  ✓ Generated {total_stories} main stories + {total_briefs} briefs")
    
    # Step 4: Render newsletter
    print(f"\n[4/4] Rendering {output_format.upper()} newsletter...")
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
        """
    )
    
    parser.add_argument(
        "--output", "-o",
        choices=["html", "markdown", "md"],
        default="html",
        help="Output format (default: html)"
    )
    
    parser.add_argument(
        "--days", "-d",
        type=int,
        default=7,
        help="How many days back to look for articles (default: 7)"
    )
    
    parser.add_argument(
        "--stories", "-s",
        type=int,
        default=3,
        help="Number of main stories per section (default: 3)"
    )
    
    parser.add_argument(
        "--title", "-t",
        default="The Second Curves Media & Events Brief",
        help="Newsletter title"
    )
    
    parser.add_argument(
        "--sources-folder",
        help="Path to folder containing your collected sources"
    )
    
    parser.add_argument(
        "--out-file", "-f",
        help="Output file path (default: prints to stdout)"
    )
    
    parser.add_argument(
        "--api-key",
        help="Anthropic API key (or set ANTHROPIC_API_KEY env var)"
    )
    
    parser.add_argument(
        "--footer",
        default="Published by Events Industry Intelligence",
        help="Footer text for the newsletter"
    )
    
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
        exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        raise


if __name__ == "__main__":
    main()
