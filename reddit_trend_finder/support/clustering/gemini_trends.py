"""
gemini_trends.py — Build prompts, call Gemini, parse structured trend output.

Adapted from the trend_finder_kmeans_llm.ipynb notebook with:
  • HDBSCAN probability column awareness
  • Keyword + bigram + NER extraction
  • Retry logic for API calls
"""

import os
import sys
import json
import time
import textwrap
from collections import Counter

# Add parent directory (support/) to path so we can import config
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
import google.generativeai as genai
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer

from config import GEMINI_API_KEY, GEMINI_MODEL

# ────────────────────────────────────────────────────────────
# GEMINI CLIENT (lazy init)
# ────────────────────────────────────────────────────────────

_model = None


def _get_model():
    global _model
    if _model is None:
        if not GEMINI_API_KEY:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to your .env file."
            )
        genai.configure(api_key=GEMINI_API_KEY)
        _model = genai.GenerativeModel(GEMINI_MODEL)
    return _model


# ────────────────────────────────────────────────────────────
# KEYWORD / ENTITY EXTRACTION
# ────────────────────────────────────────────────────────────

def extract_keywords(texts: list[str], top_n: int = 15) -> list[str]:
    """Simple keyword extraction — stop-word filtered unigrams."""
    words = []
    for text in texts:
        tokens = str(text).lower().split()
        tokens = [
            w for w in tokens
            if w not in ENGLISH_STOP_WORDS
            and len(w) > 3
            and not w.startswith(("http", "@", "#", "www"))
            and w.isalpha()
        ]
        words.extend(tokens)
    return [w for w, _ in Counter(words).most_common(top_n)]


def extract_bigrams(titles: list[str], top_n: int = 10) -> list[str]:
    """Extract recurring 2–3 word phrases from post titles."""
    try:
        vec = CountVectorizer(
            ngram_range=(2, 3),
            stop_words="english",
            max_features=top_n,
            min_df=2,
        )
        vec.fit(titles)
        return list(vec.vocabulary_.keys())
    except Exception:
        return []


def extract_entities_simple(titles: list[str], top_n: int = 8) -> dict:
    """
    Lightweight NER using spaCy (en_core_web_sm).
    Falls back to empty dict if spaCy is not installed.
    """
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
    except Exception:
        return {}

    counts: dict[str, Counter] = {
        "ORG": Counter(),
        "PRODUCT": Counter(),
        "PERSON": Counter(),
        "GPE": Counter(),
    }

    for title in titles:
        doc = nlp(str(title)[:512])
        for ent in doc.ents:
            if ent.label_ in counts:
                counts[ent.label_][ent.text.strip()] += 1

    result = {}
    for label, counter in counts.items():
        top = [(n, c) for n, c in counter.most_common(top_n) if len(n) > 2]
        if top:
            result[label] = top
    return result


# ────────────────────────────────────────────────────────────
# SENTIMENT HEURISTIC
# ────────────────────────────────────────────────────────────

_NEGATIVE_WORDS = frozenset({
    "ban", "fail", "broken", "worst", "hate", "scam", "fraud",
    "wrong", "bad", "terrible", "dangerous", "illegal", "blocked",
    "cancelled", "delayed", "fined", "crash", "layoff", "leak",
})


def _guess_sentiment(titles: pd.Series) -> tuple[str, float]:
    lower = titles.str.lower()
    neg_pct = lower.apply(
        lambda t: any(w in t for w in _NEGATIVE_WORDS)
    ).mean()
    if neg_pct > 0.5:
        label = "mostly negative/critical"
    elif neg_pct < 0.2:
        label = "mostly positive/excited"
    else:
        label = "mixed sentiment"
    return label, neg_pct


# ────────────────────────────────────────────────────────────
# BUILD CONTEXT BLOCK (per cluster)
# ────────────────────────────────────────────────────────────

def build_cluster_context(
    df_cluster: pd.DataFrame,
    cluster_id: int,
    top_posts: pd.DataFrame,
) -> str:
    """
    Build a text block summarising one cluster for the LLM prompt.

    Parameters
    ----------
    df_cluster : all posts in this cluster
    cluster_id : cluster label
    top_posts  : pre-selected top posts (probability + engagement ranked)
    """
    grp = df_cluster

    # Keywords & bigrams
    text_col = "text_translated" if "text_translated" in grp.columns else "full_text"
    keywords = extract_keywords(grp[text_col].tolist(), top_n=15)
    bigrams = extract_bigrams(grp["title"].tolist())

    # Sentiment
    sentiment_label, neg_pct = _guess_sentiment(grp["title"])

    # NER
    entities = extract_entities_simple(grp["title"].tolist())
    label_map = {
        "ORG": "🏢 Companies/Orgs",
        "PRODUCT": "📦 Products/Services",
        "PERSON": "👤 People",
        "GPE": "🌍 Places",
    }
    entity_lines = []
    for label, items in entities.items():
        names = ", ".join(f"{n} ({c}x)" for n, c in items)
        entity_lines.append(f"  {label_map.get(label, label)}: {names}")
    entity_block = "\n".join(entity_lines) if entity_lines else "  None detected"

    # Assemble
    lines = [
        f"--- CLUSTER {cluster_id} ---",
        f"Post count         : {len(grp)}",
        f"Avg score          : {grp['score'].mean():.0f}",
        f"Avg comments       : {grp['num_comments'].mean():.0f}",
        f"Avg upvote ratio   : {grp['upvote_ratio'].mean():.2f}",
        f"Community sentiment: {sentiment_label} ({neg_pct:.0%} posts are critical)",
        "",
        f"Recurring keywords : {', '.join(keywords)}",
        f"Recurring phrases  : {', '.join(bigrams) if bigrams else 'n/a'}",
        "",
        "Named entities mentioned across posts (frequency in brackets):",
        entity_block,
        "",
        "Top posts by representativeness + engagement:",
    ]

    for i, (_, row) in enumerate(top_posts.iterrows(), 1):
        prob = row.get("probability", 0)
        lines.append(
            f"  {i}. [Score: {int(row['score']):,} | "
            f"Comments: {int(row['num_comments']):,} | "
            f"Prob: {prob:.2f}] "
            f"{str(row['title'])[:120]}"
        )
        if "permalink" in row and pd.notna(row["permalink"]):
            lines.append(f"     URL: {row['permalink']}")

    return "\n".join(lines)


# ────────────────────────────────────────────────────────────
# BUILD FULL PROMPT
# ────────────────────────────────────────────────────────────

def build_prompt(
    niche: str,
    cluster_contexts: list[str],
    week_label: str = "last 7 days",
) -> str:
    context_block = "\n\n".join(cluster_contexts)
    n = len(cluster_contexts)

    # Build dynamic JSON example based on actual cluster count
    trend_examples = []
    for i in range(1, n + 1):
        if i == 1:
            trend_examples.append(f"""\
    {{
      "rank": {i},
      "title": "Trend title here",
      "description": "Description here.",
      "key_entities": {{
        "companies": ["e.g. Google", "Microsoft"],
        "products": ["e.g. ChatGPT"],
        "people": ["e.g. Elon Musk"]
      }},
      "sentiment": "positive",
      "importance": "Why this trend matters in one sentence.",
      "references": [
        "https://reddit.com/...",
        "https://reddit.com/..."
      ]
    }}""")
        else:
            trend_examples.append(f"""\
    {{
      "rank": {i},
      "title": "...",
      "description": "...",
      "key_entities": {{"companies": [], "products": [], "people": []}},
      "sentiment": "mixed",
      "importance": "...",
      "references": ["..."]
    }}""")

    trends_json = ",\n".join(trend_examples)

    return textwrap.dedent(f"""\
You are a social media trend analyst specializing in identifying emerging patterns on Reddit.

Below is cluster data from r/{niche}. Each cluster is a group of posts that Reddit users \
have been repeatedly discussing during {week_label}.

IMPORTANT DISTINCTION:
- A NEWS EVENT is a single specific thing that happened (e.g. "Company X fined $1M")
- A TREND is a PATTERN — a topic, sentiment, or concern that appears repeatedly across \
many posts and is gaining momentum

Your job is to identify TRENDS, not summarize news events.

REDDIT CLUSTER DATA ({week_label}):
{context_block}

You are given {n} cluster(s) above. Generate EXACTLY {n} trend(s) — one trend per cluster. \
Do NOT generate more or fewer than {n}.

A good trend answer:
✅ Describes a pattern seen across many posts, not a single event
✅ Explains WHY this topic keeps coming up and what it signals about community sentiment
✅ Is forward-looking — what does this pattern suggest is building or shifting?
✅ Mentions specific companies, products, or people from the Named Entities if central
✅ Uses specific posts as evidence/references, not as the trend itself

For each trend provide:
1. TREND TITLE — short, pattern-based, max 10 words
2. DESCRIPTION — 3 sentences: (a) what pattern is emerging, (b) why the community \
keeps discussing it, (c) what it signals
3. KEY ENTITIES — list any companies, products, or people central to this trend
4. SENTIMENT — overall sentiment of the trend (positive / negative / mixed)
5. IMPORTANCE — one sentence on why this trend matters
6. REFERENCES — 2-3 URLs from the top posts listed above as evidence

Respond ONLY in this JSON format, no markdown, no code fences. \
The "trends" array must contain EXACTLY {n} object(s):
{{
  "niche": "{niche}",
  "trends": [
{trends_json}
  ]
}}""")


# ────────────────────────────────────────────────────────────
# CALL GEMINI
# ────────────────────────────────────────────────────────────

def call_gemini(prompt: str, retries: int = 3, delay: int = 5) -> str | None:
    """Call Gemini API with retry logic. Returns raw text."""
    model = _get_model()
    for attempt in range(1, retries + 1):
        try:
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"  ⚠️  Attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                time.sleep(delay)
    return None


# ────────────────────────────────────────────────────────────
# PARSE RESPONSE
# ────────────────────────────────────────────────────────────

def parse_gemini_response(raw: str | None) -> dict | None:
    """Strip markdown fences and parse JSON."""
    if not raw:
        return None
    try:
        clean = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(clean)
    except json.JSONDecodeError as e:
        print(f"  ❌ JSON parse error: {e}")
        print(f"  Raw snippet: {raw[:300]}")
        return None
