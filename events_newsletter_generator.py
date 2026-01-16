#!/usr/bin/env python3
"""
The Second Curves Media & Events Brief - Newsletter Generator
--------------------------------------------------------------
A specialized newsletter for the global trade press, conference, 
and tradeshow market. Written in Axios style for board-level readers.

Usage:
    python events_newsletter_generator.py
    python events_newsletter_generator.py --sources-folder ./my_sources
    python events_newsletter_generator.py --list-articles
"""

import argparse
import json
import os
import re
import hashlib
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

DEFAULT_RECIPIENT_NAME = "Reader"

# Industry-specific RSS feeds - EDIT THIS LIST TO ADD/REMOVE SOURCES
RSS_FEEDS = {
    # Exhibition & Events Industry
    "Exhibition World": "https://www.exhibitionworld.co.uk/feed",
    "Exhibition News": "https://www.exhibitionnews.co.uk/feed",
    "Mash Media": "https://www.mashmedia.net/feed/",
    "Conference News": "https://www.conference-news.co.uk/feed",
    "Access AA": "https://accessaa.co.uk/feed/",
    "Event Industry News": "https://www.eventindustrynews.com/feed",
    "TSNN": "https://www.tsnn.com/feed",
    
    # B2B Media & Publishing
    "FIPP": "https://www.fipp.com/feed/",
    "InPublishing": "https://www.inpublishing.co.uk/feed",
    "Press Gazette": "https://pressgazette.co.uk/feed/",
    
    # Business News
    "PE Hub": "https://www.pehub.com/feed/",
    
    # Marketing & Events
    "Event Marketer": "https://www.eventmarketer.com/feed/",
    "BizBash": "https://www.bizbash.com/rss.xml",
    "Skift Meetings": "https://skift.com/meetings/feed/",
}
RSS_FEEDS = {
    # Exhibition & Events Industry
    "UFI Blog": "https://www.ufi.org/blog/feed/",  # ← ADD THIS LINE
    "Exhibition World": "https://www.exhibitionworld.co.uk/feed",
    ...
# Section definitions
SECTIONS = {
    "market_signals": {
        "title": "Market Signals",
        "icon": "📊",
        "description": "Strategic trends, market movements, and industry analysis",
        "sub_themes": None,  # Removed sub-themes
    },
    "deals": {
        "title": "Deals",
        "icon": "🤝", 
        "description": "M&A, investments, and divestitures in media and events industry",
        "sub_themes": None,
    },
    "hires_fires": {
        "title": "Hires & Fires",
        "icon": "👔",
        "description": "Executive appointments, departures, and restructuring",
        "sub_themes": None,
    }
}

# HTML Template - Helvetica 10pt, clean design
# Logo background color: #6C9F7F (matched from logo image)
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
            font-family: Helvetica, Arial, sans-serif;
            font-size: 10pt;
            max-width: 680px;
            margin: 0 auto;
            padding: 20px;
            background: #ffffff;
            color: #1a1a1a;
            line-height: 1.6;
        }
        .logo-banner {
            background: #6C9F7F;
            padding: 25px 20px;
            text-align: center;
            border-radius: 8px 8px 0 0;
        }
        .logo-banner img {
            max-width: 240px;
            height: auto;
        }
        .logo-text {
            color: white;
            font-size: 18pt;
            font-weight: bold;
            letter-spacing: 1px;
        }
        .header {
            background: #6C9F7F;
            padding: 0 20px 20px 20px;
            margin-bottom: 25px;
            border-radius: 0 0 8px 8px;
            text-align: center;
        }
        .header h1 {
            font-size: 16pt;
            font-weight: 800;
            margin: 0 0 5px 0;
            color: #ffffff;
        }
        .header .tagline {
            color: rgba(255,255,255,0.85);
            font-size: 9pt;
            margin-bottom: 8px;
        }
        .header .date {
            font-size: 8pt;
            color: rgba(255,255,255,0.7);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .executive-summary {
            background: #f8f9fa;
            border-left: 4px solid #6C9F7F;
            padding: 20px;
            margin-bottom: 30px;
        }
        .executive-summary p {
            margin: 0 0 15px 0;
        }
        .executive-summary ul {
            margin: 15px 0;
            padding-left: 20px;
            list-style-type: disc;
        }
        .executive-summary li {
            margin-bottom: 10px;
            line-height: 1.5;
        }
        .section {
            margin-bottom: 35px;
        }
        .section-header {
            display: flex;
            align-items: center;
            border-bottom: 2px solid #6C9F7F;
            padding-bottom: 8px;
            margin-bottom: 20px;
        }
        .section-header h2 {
            font-size: 12pt;
            font-weight: 800;
            margin: 0;
            color: #1a1a1a;
        }
        .section-header .icon {
            font-size: 12pt;
            margin-right: 8px;
        }
        .sub-theme {
            font-size: 9pt;
            font-weight: 700;
            color: #5a7a5a;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin: 20px 0 12px 0;
            padding-bottom: 5px;
            border-bottom: 1px dashed #6C9F7F;
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
            font-size: 11pt;
            font-weight: 700;
            margin: 0 0 8px 0;
            line-height: 1.3;
        }
        .story .meta {
            font-size: 8pt;
            color: #888;
            margin-bottom: 12px;
        }
        .story .meta a {
            color: #5a7a5a;
            text-decoration: none;
        }
        .story .meta a:hover {
            text-decoration: underline;
        }
        .story .label {
            font-weight: 700;
            color: #5a7a5a;
            font-size: 8pt;
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
            font-size: 8pt;
            color: #5a7a5a;
            text-decoration: none;
            font-weight: 600;
        }
        .story .source-link:hover {
            text-decoration: underline;
        }
        .footer {
            background: #6C9F7F;
            margin-top: 40px;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            font-size: 8pt;
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
        <div class="logo-text">SECOND CURVE CONSULTING</div>
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
                    <div class="meta">
                        {% if story.link %}<a href="{{ story.link }}" target="_blank">{{ story.source_display }}</a>{% else %}{{ story.source_display }}{% endif %} • {{ story.published }}
                    </div>
                    {{ story.summary | safe }}
                </div>
                {% endif %}
                {% endfor %}
                {% endfor %}
            {% else %}
                {% for story in section_data.stories %}
                <div class="story">
                    <h3>{{ story.headline }}</h3>
                    <div class="meta">
                        {% if story.link %}<a href="{{ story.link }}" target="_blank">{{ story.source_display }}</a>{% else %}{{ story.source_display }}{% endif %} • {{ story.published }}
                    </div>
                    {{ story.summary | safe }}
                    {% if story.link %}
                    <a href="{{ story.link }}" target="_blank" class="source-link">Read source →</a>
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

*{{ story.source_display }} • {{ story.published }}*

{{ story.summary }}

{% if story.link %}[Read source →]({{ story.link }}){% endif %}

---

{% endif %}
{% endfor %}
{% endfor %}
{% else %}
{% for story in section_data.stories %}
### {{ story.headline }}

*{{ story.source_display }} • {{ story.published }}*

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

*{{ footer_text | default('Published by Second Curve Consulting') }}*
"""

# =============================================================================
# CORE FUNCTIONS
# =============================================================================

def get_domain_from_url(url: str) -> str:
    """Extract clean domain name from URL for display."""
    if not url:
        return "Unknown"
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        # Capitalize nicely
        return domain.split('.')[0].title() if domain else "Unknown"
    except:
        return "Unknown"


def deduplicate_articles(articles: list) -> list:
    """Remove duplicate articles based on title similarity and URL."""
    seen_hashes = set()
    unique_articles = []
    
    for article in articles:
        # Create hash from normalized title
        title_normalized = re.sub(r'[^a-z0-9]', '', article['title'].lower())[:50]
        url_hash = hashlib.md5(article.get('link', '').encode()).hexdigest()[:10]
        
        # Use combination of title and URL
        article_hash = f"{title_normalized}_{url_hash}"
        
        if article_hash not in seen_hashes:
            seen_hashes.add(article_hash)
            unique_articles.append(article)
    
    return unique_articles


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
                
                link = entry.get('link', '')
                
                articles.append({
                    "source": source_name,
                    "source_display": source_name,  # Use the feed name, not "User Source"
                    "title": entry.get('title', 'Untitled'),
                    "link": link,
                    "content": content,
                    "published": pub_date.strftime("%d %B %Y"),
                    "pub_timestamp": pub_date.timestamp(),
                    "from_user_sources": False
                })
                
        except Exception as e:
            print(f"    ⚠️  Error: {e}")
    
    articles.sort(key=lambda x: x['pub_timestamp'], reverse=True)
    
    # Deduplicate
    original_count = len(articles)
    articles = deduplicate_articles(articles)
    if original_count != len(articles):
        print(f"  ✓ Removed {original_count - len(articles)} duplicates")
    
    print(f"  ✓ Fetched {len(articles)} unique articles from RSS feeds")
    return articles


def load_user_sources(sources_folder: str) -> list:
    """Load articles from user-provided sources folder."""
    articles = []
    folder = Path(sources_folder)
    
    if not folder.exists():
        print(f"  Sources folder not found: {sources_folder}")
        return articles
    
    print(f"  Loading user sources from {sources_folder}...")
    
    for subfolder in [folder] + [f for f in folder.iterdir() if f.is_dir()]:
        # Process text files
        for txt_file in subfolder.glob("*.txt"):
            if txt_file.name.lower() == 'readme.txt':
                continue
            try:
                content = txt_file.read_text(encoding='utf-8')
                lines = content.strip().split('\n')
                
                # Check if it's a URL list
                non_comment_lines = [l.strip() for l in lines if l.strip() and not l.strip().startswith('#')]
                if all(line.startswith(('http://', 'https://')) for line in non_comment_lines):
                    for url in non_comment_lines:
                        domain = get_domain_from_url(url)
                        articles.append({
                            "source": domain,
                            "source_display": domain,
                            "title": f"Article from {domain}",
                            "link": url,
                            "content": f"[URL: {url}]",
                            "published": datetime.now().strftime("%d %B %Y"),
                            "pub_timestamp": datetime.now().timestamp(),
                            "from_user_sources": True
                        })
                else:
                    # It's article content
                    title = txt_file.stem.replace("_", " ").replace("-", " ").title()
                    articles.append({
                        "source": "Curated",
                        "source_display": "Curated Source",
                        "title": title,
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
                items = data if isinstance(data, list) else [data]
                
                for item in items:
                    link = item.get("link", item.get("url", ""))
                    source = item.get("source", get_domain_from_url(link))
                    articles.append({
                        "source": source,
                        "source_display": source,
                        "title": item.get("title", "Untitled"),
                        "link": link,
                        "content": item.get("content", item.get("summary", ""))[:3000],
                        "published": item.get("published", datetime.now().strftime("%d %B %Y")),
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
                    "source": "Curated",
                    "source_display": "Curated Source",
                    "title": title,
                    "link": "",
                    "content": content[:3000],
                    "published": datetime.now().strftime("%d %B %Y"),
                    "pub_timestamp": datetime.now().timestamp(),
                    "from_user_sources": True
                })
            except Exception as e:
                print(f"    ⚠️  Error reading {md_file}: {e}")
    
    # Deduplicate user sources too
    articles = deduplicate_articles(articles)
    print(f"  ✓ Loaded {len(articles)} user-provided sources")
    return articles


def generate_article_list(articles: list, output_format: str = "html") -> str:
    """Generate an interactive article list with checkboxes for easy selection."""
    
    HIGH_PRIORITY_KEYWORDS = [
        "investment", "investor", "private equity", "PE", "acquisition", "acquire",
        "merger", "M&A", "funding", "capital", "valuation", "IPO", "stake",
        "buy", "sell", "deal", "transaction", "billion", "million",
        "global", "international", "cross-border", "export", "import", "trade",
        "foreign", "overseas", "expansion", "enter", "market entry", "launch",
        "Asia", "Europe", "Americas", "Middle East", "China", "India", "US", "UK",
        "Germany", "France", "Dubai", "Singapore", "emerging market",
        "revenue", "growth", "profit", "margin", "earnings", "forecast",
        "outlook", "performance", "results", "quarter", "annual",
        "strategy", "restructur", "pivot", "shift", "transform", "digital",
        "CEO", "appoint", "hire", "depart", "leadership"
    ]
    
    def score_article(article):
        text = f"{article['title']} {article['content']}".lower()
        score = 0
        matched = []
        
        for kw in HIGH_PRIORITY_KEYWORDS:
            if kw.lower() in text:
                score += 3
                if kw not in matched:
                    matched.append(kw)
        
        if article.get('from_user_sources'):
            score += 10
        
        return score, matched[:5]
    
    def generate_synopsis(title, content):
        """Generate a brief synopsis from title and content."""
        # Clean content
        text = content[:500].strip()
        # Get first sentence or first 150 chars
        sentences = re.split(r'[.!?]', text)
        if sentences and len(sentences[0]) > 20:
            synopsis = sentences[0].strip()[:200]
        else:
            synopsis = text[:200]
        return synopsis + "..." if len(synopsis) >= 200 else synopsis
    
    scored = []
    for i, article in enumerate(articles):
        score, keywords = score_article(article)
        scored.append({
            **article,
            'index': i + 1,
            'relevance_score': score,
            'matched_keywords': keywords,
            'synopsis': generate_synopsis(article['title'], article['content'])
        })
    
    scored.sort(key=lambda x: x['relevance_score'], reverse=True)
    
    # Generate interactive HTML with checkboxes
    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Article Selection - Second Curves Brief</title>
    <style>
        body { font-family: Helvetica, Arial, sans-serif; font-size: 10pt; max-width: 950px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
        h1 { color: #1a1a1a; border-bottom: 3px solid #6C9F7F; padding-bottom: 10px; margin-bottom: 5px; }
        .subtitle { color: #666; margin-bottom: 20px; }
        
        .selection-box {
            background: #6C9F7F;
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            position: sticky;
            top: 10px;
            z-index: 100;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }
        .selection-box label { font-weight: bold; }
        #selected-output {
            background: white;
            color: #1a1a1a;
            padding: 8px 12px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 11pt;
            margin: 10px 0;
            min-height: 20px;
            word-break: break-all;
        }
        .copy-btn {
            background: white;
            color: #6C9F7F;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
            font-size: 10pt;
        }
        .copy-btn:hover { background: #f0f0f0; }
        .count { font-size: 12pt; font-weight: bold; }
        
        .filters { margin-bottom: 15px; }
        .filter-btn {
            background: white;
            border: 1px solid #ddd;
            padding: 5px 12px;
            border-radius: 15px;
            cursor: pointer;
            margin-right: 5px;
            font-size: 9pt;
        }
        .filter-btn:hover { background: #f0f0f0; }
        .filter-btn.active { background: #6C9F7F; color: white; border-color: #6C9F7F; }
        
        .article {
            background: white;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 10px;
            border-left: 4px solid #ddd;
            display: flex;
            align-items: flex-start;
            gap: 12px;
        }
        .article.high { border-left-color: #22c55e; }
        .article.medium { border-left-color: #f59e0b; }
        .article.selected { background: #f0fff4; border-left-color: #6C9F7F; }
        
        .article input[type="checkbox"] {
            width: 20px;
            height: 20px;
            margin-top: 3px;
            cursor: pointer;
            accent-color: #6C9F7F;
        }
        
        .article-content { flex: 1; }
        .article-header { display: flex; justify-content: space-between; align-items: center; }
        .article-number { 
            background: #6C9F7F; 
            color: white; 
            padding: 2px 8px; 
            border-radius: 4px; 
            font-weight: bold; 
            font-size: 9pt; 
        }
        .score { font-size: 9pt; padding: 2px 6px; border-radius: 4px; }
        .score.high { background: #dcfce7; color: #166534; }
        .score.medium { background: #fef3c7; color: #92400e; }
        .score.low { background: #f3f4f6; color: #6b7280; }
        
        .article-title { 
            font-size: 12pt; 
            font-weight: 700; 
            margin: 8px 0 5px 0; 
            color: #1a1a1a;
            line-height: 1.3;
        }
        .article-title a { color: #1a1a1a; text-decoration: none; }
        .article-title a:hover { color: #6C9F7F; text-decoration: underline; }
        
        .article-meta { font-size: 9pt; color: #888; margin-bottom: 8px; }
        
        .article-synopsis {
            font-size: 10pt;
            color: #333;
            line-height: 1.5;
            margin: 10px 0;
            padding: 10px;
            background: #fafafa;
            border-radius: 4px;
        }
        
        .keywords { margin-top: 8px; }
        .keyword { 
            background: #e5e7eb; 
            color: #374151; 
            padding: 2px 8px; 
            border-radius: 10px; 
            font-size: 8pt; 
            margin-right: 4px;
            display: inline-block;
            margin-bottom: 3px;
        }
        
        .instructions {
            background: #fffbeb;
            border: 1px solid #f59e0b;
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
            font-size: 9pt;
        }
        .instructions ol { margin: 10px 0; padding-left: 20px; }
        .instructions li { margin-bottom: 5px; }
    </style>
</head>
<body>
    <h1>📋 Select Articles for Newsletter</h1>
    <p class="subtitle">Check the articles you want to include, then copy the numbers below</p>
    
    <div class="selection-box">
        <label>Selected Articles (<span class="count" id="count">0</span>):</label>
        <div id="selected-output">None selected</div>
        <button class="copy-btn" onclick="copySelection()">📋 Copy to Clipboard</button>
        <button class="copy-btn" onclick="clearAll()">✖ Clear All</button>
        <button class="copy-btn" onclick="selectHigh()">⭐ Select All HIGH</button>
    </div>
    
    <div class="filters">
        <button class="filter-btn active" onclick="filterArticles('all')">All (""" + str(len(scored)) + """)</button>
        <button class="filter-btn" onclick="filterArticles('high')">High (""" + str(len([a for a in scored if a['relevance_score'] >= 9])) + """)</button>
        <button class="filter-btn" onclick="filterArticles('medium')">Medium (""" + str(len([a for a in scored if 3 <= a['relevance_score'] < 9])) + """)</button>
        <button class="filter-btn" onclick="filterArticles('low')">Low (""" + str(len([a for a in scored if a['relevance_score'] < 3])) + """)</button>
    </div>
"""
    
    for article in scored:
        score = article['relevance_score']
        rel_class = "high" if score >= 9 else "medium" if score >= 3 else "low"
        score_class = "high" if score >= 9 else "medium" if score >= 3 else "low"
        score_label = "HIGH" if score >= 9 else "MEDIUM" if score >= 3 else "LOW"
        
        link = article.get('link', '')
        title_html = f'<a href="{link}" target="_blank">{article["title"]}</a>' if link else article["title"]
        source_display = article.get('source_display', article.get('source', 'Unknown'))
        
        keywords_html = ''.join(f'<span class="keyword">{kw}</span>' for kw in article['matched_keywords']) if article['matched_keywords'] else ''
        
        synopsis = article.get('synopsis', article['content'][:200])
        
        html += f"""
    <div class="article {rel_class}" data-relevance="{rel_class}">
        <input type="checkbox" id="article-{article['index']}" value="{article['index']}" onchange="updateSelection()">
        <div class="article-content">
            <div class="article-header">
                <span class="article-number">#{article['index']}</span>
                <span class="score {score_class}">{score_label}</span>
            </div>
            <div class="article-title">{title_html}</div>
            <div class="article-meta">{source_display} • {article['published']}</div>
            <div class="article-synopsis">{synopsis}</div>
            <div class="keywords">{keywords_html}</div>
        </div>
    </div>
"""
    
    html += """
    <div class="instructions">
        <strong>📝 How to use:</strong>
        <ol>
            <li>Check the articles you want in your newsletter</li>
            <li>Click "Copy to Clipboard"</li>
            <li>Go to GitHub Actions → Run workflow</li>
            <li>Paste into the "Article numbers to include" field</li>
            <li>Run the workflow</li>
        </ol>
    </div>

    <script>
        function updateSelection() {
            const checkboxes = document.querySelectorAll('input[type="checkbox"]:checked');
            const numbers = Array.from(checkboxes).map(cb => cb.value);
            const output = document.getElementById('selected-output');
            const count = document.getElementById('count');
            
            count.textContent = numbers.length;
            output.textContent = numbers.length > 0 ? numbers.join(',') : 'None selected';
            
            // Update visual selection
            document.querySelectorAll('.article').forEach(el => el.classList.remove('selected'));
            checkboxes.forEach(cb => cb.closest('.article').classList.add('selected'));
        }
        
        function copySelection() {
            const output = document.getElementById('selected-output').textContent;
            if (output !== 'None selected') {
                navigator.clipboard.writeText(output);
                alert('Copied: ' + output);
            }
        }
        
        function clearAll() {
            document.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
            updateSelection();
        }
        
        function selectHigh() {
            document.querySelectorAll('.article.high input[type="checkbox"]').forEach(cb => cb.checked = true);
            updateSelection();
        }
        
        function filterArticles(filter) {
            document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            
            document.querySelectorAll('.article').forEach(el => {
                if (filter === 'all') {
                    el.style.display = 'flex';
                } else {
                    el.style.display = el.dataset.relevance === filter ? 'flex' : 'none';
                }
            });
        }
    </script>
</body>
</html>"""
    
    return html


def generate_executive_summary(sections_content: dict, api_key: str) -> str:
    """Generate simple 3-bullet executive summary as HTML."""
    
    client = Anthropic(api_key=api_key)
    
    # Get all selected stories
    all_stories = []
    for section_data in sections_content.values():
        for story in section_data.get("stories", []):
            all_stories.append(f"- {story['headline']}: {story.get('summary', '')[:200]}")
    
    stories_text = "\n".join(all_stories[:10])
    
    prompt = f"""Based on these newsletter stories, write a brief executive summary.

STORIES:
{stories_text}

REQUIREMENTS:
1. Start with "Good morning,"
2. Write ONE sentence (max 20 words) setting the context
3. Then write exactly 3 bullet points summarizing the key themes
4. Each bullet should be 1 line max, answer "so what?" for executives
5. Simple, direct language

Return ONLY in this exact format (no markdown, plain text):
Good morning,

[One sentence context here]

- [First bullet point]
- [Second bullet point]
- [Third bullet point]"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    
    text = response.content[0].text.strip()
    
    # Convert to proper HTML
    lines = text.split('\n')
    html_parts = []
    bullets = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('- ') or line.startswith('• '):
            bullets.append(line[2:])
        else:
            if bullets:
                # Output accumulated bullets
                html_parts.append('<ul>' + ''.join(f'<li>{b}</li>' for b in bullets) + '</ul>')
                bullets = []
            html_parts.append(f'<p>{line}</p>')
    
    # Don't forget remaining bullets
    if bullets:
        html_parts.append('<ul>' + ''.join(f'<li>{b}</li>' for b in bullets) + '</ul>')
    
    return '\n'.join(html_parts)


def categorize_and_write_newsletter(
    articles: list, 
    api_key: Optional[str] = None,
    custom_instructions: Optional[str] = None,
    stories_per_section: int = 3,
    include_articles: Optional[List[int]] = None,
    exclude_articles: Optional[List[int]] = None
) -> dict:
    """Use Claude to categorize articles and write newsletter sections."""
    
    if not api_key:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
    
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found.")
    
    if not custom_instructions:
        custom_instructions = os.environ.get("EXTRA_PROMPT", "")
    
    client = Anthropic(api_key=api_key)
    
    # Filter articles
    if exclude_articles:
        articles = [a for i, a in enumerate(articles) if (i+1) not in exclude_articles]
    
    # Prepare articles text
    articles_text = ""
    for i, article in enumerate(articles[:60]):
        user_flag = " [PRIORITIZE]" if article.get('from_user_sources') else ""
        include_flag = " [MUST INCLUDE]" if include_articles and (i+1) in include_articles else ""
        articles_text += f"""
---
[{i+1}]{user_flag}{include_flag}
Title: {article['title']}
Source: {article.get('source_display', article['source'])}
Link: {article.get('link', 'N/A')}
Content: {article['content'][:800]}
---
"""
    
    prompt = f"""Analyze these articles and write a newsletter with 3 sections in Axios bullet-point style.

SECTIONS:
1. MARKET SIGNALS - Strategic trends affecting the B2B media, exhibitions and events industry
2. DEALS - M&A, investments, and divestitures ONLY in the media, exhibitions, conferences, and events industry (ignore deals in other sectors)
3. HIRES & FIRES - Executive moves in media and events companies

RULES:
- {stories_per_section} stories per section (if enough relevant content)
- Articles marked [MUST INCLUDE] or [PRIORITIZE] get priority
- For DEALS: Only include M&A activity directly related to media companies, event organizers, exhibition companies, conference businesses, or trade publishers
- Skip any deals in unrelated industries (tech, retail, healthcare etc) unless they directly impact events/media

WRITING STYLE (Axios):
- Each story needs: headline, then 3 bullets max
- Format bullets as: "Why it matters:", "The details:", "What to watch:"
- Keep each bullet to 1-2 lines
- Direct, punchy language

{f"INSTRUCTIONS: {custom_instructions}" if custom_instructions else ""}

ARTICLES:
{articles_text}

Return JSON:
{{
    "sections": {{
        "market_signals": {{
            "stories": [
                {{
                    "article_index": 1,
                    "headline": "Clear headline",
                    "summary": "<span class='label'>Why it matters:</span><ul><li>Point</li></ul><span class='label'>The details:</span><ul><li>Point</li></ul><span class='label'>What to watch:</span><ul><li>Point</li></ul>"
                }}
            ]
        }},
        "deals": {{"stories": [...]}},
        "hires_fires": {{"stories": [...]}}
    }}
}}

Return ONLY valid JSON."""

    print("  Writing newsletter...")
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=6000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    response_text = response.content[0].text
    
    try:
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        result = json.loads(json_match.group()) if json_match else json.loads(response_text)
    except json.JSONDecodeError as e:
        print(f"  ⚠️  JSON error: {e}")
        raise
    
    # Enrich with original data
    enriched_sections = {}
    
    for section_key, section_config in SECTIONS.items():
        section_data = result.get("sections", {}).get(section_key, {})
        
        enriched_stories = []
        for story in section_data.get("stories", []):
            idx = story.get("article_index", 1) - 1
            if 0 <= idx < len(articles):
                orig = articles[idx]
                link = orig.get('link', '')
                source_display = orig.get('source_display', orig.get('source', ''))
                
                # If source is generic, use domain from URL
                if source_display in ['User Source', 'Curated', '']:
                    source_display = get_domain_from_url(link) if link else 'Curated Source'
                
                enriched_stories.append({
                    "headline": story.get("headline", orig["title"]),
                    "summary": story.get("summary", ""),
                    "source": orig.get("source", ""),
                    "source_display": source_display,
                    "link": link,
                    "published": orig["published"],
                    "sub_theme": story.get("sub_theme")
                })
        
        enriched_sections[section_key] = {
            "title": section_config["title"],
            "icon": section_config["icon"],
            "stories": enriched_stories,
            "sub_themes": section_config.get("sub_themes")
        }
    
    return {"sections": enriched_sections}


def render_newsletter(
    content: dict, 
    output_format: str = "html",
    title: str = "The Second Curves Media & Events Brief",
    footer_text: str = None,
    executive_summary: str = None,
    logo_url: str = None
) -> str:
    """Render newsletter to HTML or Markdown."""
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
    """Main function to generate newsletter."""
    
    if not api_key:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
    
    feeds = custom_feeds or RSS_FEEDS
    
    print("\n" + "=" * 60)
    print("📰 THE SECOND CURVES MEDIA & EVENTS BRIEF")
    print("=" * 60)
    
    print(f"\n[1/5] Fetching articles...")
    articles = fetch_feeds(feeds, days_back)
    
    if sources_folder:
        print(f"\n[2/5] Loading user sources...")
        user_articles = load_user_sources(sources_folder)
        articles = user_articles + articles
        # Deduplicate combined list
        articles = deduplicate_articles(articles)
    else:
        print(f"\n[2/5] No user sources folder...")
    
    print(f"\n  Total unique articles: {len(articles)}")
    
    if not articles:
        return "No articles found."
    
    if list_articles_only:
        return generate_article_list(articles)
    
    print(f"\n[3/5] Writing newsletter...")
    content = categorize_and_write_newsletter(
        articles, 
        api_key,
        stories_per_section=stories_per_section,
        include_articles=include_articles,
        exclude_articles=exclude_articles
    )
    
    print(f"\n[4/5] Generating summary...")
    exec_summary = generate_executive_summary(content["sections"], api_key)
    
    print(f"\n[5/5] Rendering...")
    newsletter = render_newsletter(
        content, output_format, title, footer_text, exec_summary, logo_url
    )
    
    print("\n" + "=" * 60)
    print("✅ DONE!")
    print("=" * 60 + "\n")
    
    return newsletter


def main():
    parser = argparse.ArgumentParser(description="Generate The Second Curves Media & Events Brief")
    
    parser.add_argument("--output", "-o", choices=["html", "markdown", "md"], default="html")
    parser.add_argument("--days", "-d", type=int, default=7)
    parser.add_argument("--stories", "-s", type=int, default=3)
    parser.add_argument("--title", "-t", default="The Second Curves Media & Events Brief")
    parser.add_argument("--sources-folder", help="Path to sources folder")
    parser.add_argument("--out-file", "-f", help="Output file path")
    parser.add_argument("--api-key", help="Anthropic API key")
    parser.add_argument("--footer", default="Published by Second Curve Consulting")
    parser.add_argument("--recipient", default="Reader")
    parser.add_argument("--list-articles", action="store_true")
    parser.add_argument("--include", type=str, help="Article numbers to include")
    parser.add_argument("--exclude", type=str, help="Article numbers to exclude")
    parser.add_argument("--logo", type=str, help="URL or path to logo")
    
    args = parser.parse_args()
    
    include = [int(x.strip()) for x in args.include.split(",")] if args.include else None
    exclude = [int(x.strip()) for x in args.exclude.split(",")] if args.exclude else None
    
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
            include_articles=include,
            exclude_articles=exclude,
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
