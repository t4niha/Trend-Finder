"""
main.py — FastAPI backend for the Reddit Trend Finder.

Endpoints:
  GET  /                           → welcome message
  GET  /health                     → system health check
  GET  /api/v1/niches              → list all niches with summaries
  GET  /api/v1/trends/{niche}      → trends for a niche (optionally filtered by week)
  GET  /api/v1/weekly-summary      → week-by-week breakdown for a niche
  POST /api/v1/reload              → reload trends from disk

Start:
    cd support
    python -m backend.main
  or:
    cd support
    uvicorn backend.main:app --reload
"""

import os
import sys
import asyncio

# Add support/ directory (parent) to path so we can import config
_SUPPORT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _SUPPORT_DIR not in sys.path:
    sys.path.insert(0, _SUPPORT_DIR)

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config import API_HOST, API_PORT, CORS_ORIGINS, GEMINI_MODEL
from backend.models import (
    TrendResponse,
    WeekResult,
    AllNichesSummary,
    NicheSummary,
    HealthResponse,
)
from backend.database import (
    get_available_niches,
    get_niche_results,
    get_niche_week,
    get_all_summaries,
    get_metadata,
    reload_trends,
)

# ────────────────────────────────────────────────────────────
# APP
# ────────────────────────────────────────────────────────────

app = FastAPI(
    title="Reddit Trend Finder API",
    description="Weekly HDBSCAN clustering + Gemini LLM trend analysis for Reddit niches.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ────────────────────────────────────────────────────────────
# ENDPOINTS
# ────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "service": "Reddit Trend Finder API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", response_model=HealthResponse)
def health():
    niches = get_available_niches()
    return HealthResponse(
        status="ok",
        database="connected" if niches else "no data loaded",
        trends_loaded=len(niches) > 0,
        niches=niches,
    )


@app.get("/api/v1/niches", response_model=AllNichesSummary)
def list_niches():
    """List all niches with summary statistics."""
    meta = get_metadata()
    summaries = get_all_summaries()
    return AllNichesSummary(
        generated_at=meta.get("generated_at", ""),
        model=meta.get("model", GEMINI_MODEL),
        niches=[NicheSummary(**s) for s in summaries],
    )


@app.get("/api/v1/trends/{niche}", response_model=TrendResponse)
async def get_trends(
    niche: str,
    week: int | None = Query(None, ge=1, le=53, description="ISO week number"),
):
    """
    Get trends for a niche, optionally filtered by week.

    Examples:
        /api/v1/trends/technology          → all weeks
        /api/v1/trends/technology?week=14  → week 14 only
    """
    available = get_available_niches()
    if niche not in available:
        raise HTTPException(
            status_code=404,
            detail=f"Niche '{niche}' not found. Available: {available}",
        )

    # Simulate clustering + LLM processing time for realism
    await asyncio.sleep(1)

    if week is not None:
        result = get_niche_week(niche, week)
        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"No data for r/{niche} week {week}.",
            )
        return TrendResponse(
            niche=niche,
            week=week,
            results=[WeekResult(**result)],
        )

    results = get_niche_results(niche)
    return TrendResponse(
        niche=niche,
        week=None,
        results=[WeekResult(**r) for r in results],
    )


@app.get("/api/v1/weekly-summary")
def weekly_summary(
    niche: str = Query(..., description="Niche name"),
):
    """
    Detailed week-by-week summary for a niche.

    Example: /api/v1/weekly-summary?niche=technology
    """
    available = get_available_niches()
    if niche not in available:
        raise HTTPException(
            status_code=404,
            detail=f"Niche '{niche}' not found. Available: {available}",
        )

    results = get_niche_results(niche)
    weeks = []
    for r in results:
        weeks.append({
            "week_number": r.get("week_number"),
            "week_label": r.get("week_label"),
            "post_count": r.get("post_count", 0),
            "clusters_found": r.get("clusters_found", 0),
            "noise_posts": r.get("noise_posts", 0),
            "trend_count": len(r.get("trends", [])),
            "top_trends": [
                {"rank": t["rank"], "title": t["title"]}
                for t in r.get("trends", [])
            ],
        })

    return {"niche": niche, "weeks": weeks}


@app.post("/api/v1/reload")
def reload():
    """Reload trends from output/weekly_trends.json."""
    data = reload_trends()
    niches = list(data.get("results", {}).keys())
    return {"status": "reloaded", "niches": niches}


# ────────────────────────────────────────────────────────────
# ENTRYPOINT
# ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n🚀 Starting Reddit Trend Finder API on {API_HOST}:{API_PORT}")
    print(f"   Docs: http://localhost:{API_PORT}/docs\n")
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True,
    )
