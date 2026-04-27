"""
database.py — Data access layer for the FastAPI backend.

Loads pre-generated trends from output/weekly_trends.json and provides
query functions for the API endpoints. Also queries PostgreSQL for
live post data when needed.
"""

import json
import os
from functools import lru_cache

import pandas as pd

# Resolve paths — output/ is in support/ (one level up from backend/)
_SUPPORT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_OUTPUT_FILE = os.path.join(_SUPPORT_DIR, "output", "weekly_trends.json")


def _load_trends() -> dict:
    """Load the generated trends JSON file."""
    if not os.path.exists(_OUTPUT_FILE):
        return {}
    with open(_OUTPUT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# Module-level cache — reloaded on server restart
_cache: dict = {}


def reload_trends():
    """Reload trends from disk into memory."""
    global _cache
    _cache = _load_trends()
    return _cache


def get_trends_data() -> dict:
    global _cache
    if not _cache:
        _cache = _load_trends()
    return _cache


# ────────────────────────────────────────────────────────────
# QUERY HELPERS
# ────────────────────────────────────────────────────────────

def get_available_niches() -> list[str]:
    data = get_trends_data()
    return list(data.get("results", {}).keys())


def get_niche_results(niche: str) -> list[dict]:
    data = get_trends_data()
    return data.get("results", {}).get(niche, [])


def get_niche_week(niche: str, week: int) -> dict | None:
    for result in get_niche_results(niche):
        if result.get("week_number") == week:
            return result
    return None


def get_niche_summary(niche: str) -> dict | None:
    results = get_niche_results(niche)
    if not results:
        return None
    total_posts = sum(r.get("post_count", 0) for r in results)
    weeks = [r.get("week_number") for r in results]
    total_trends = sum(len(r.get("trends", [])) for r in results)
    return {
        "niche": niche,
        "total_posts": total_posts,
        "weeks_available": sorted(weeks),
        "total_trends": total_trends,
    }


def get_all_summaries() -> list[dict]:
    summaries = []
    for niche in get_available_niches():
        s = get_niche_summary(niche)
        if s:
            summaries.append(s)
    return summaries


def get_metadata() -> dict:
    data = get_trends_data()
    return {
        "generated_at": data.get("generated_at", "unknown"),
        "model": data.get("model", "unknown"),
    }