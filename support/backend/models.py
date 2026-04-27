"""
models.py — Pydantic schemas for the Trend Finder API.
"""

from pydantic import BaseModel, Field


class KeyEntities(BaseModel):
    companies: list[str] = Field(default_factory=list)
    products: list[str] = Field(default_factory=list)
    people: list[str] = Field(default_factory=list)


class Trend(BaseModel):
    rank: int
    title: str
    description: str
    key_entities: KeyEntities = Field(default_factory=KeyEntities)
    sentiment: str = "mixed"
    importance: str = ""
    references: list[str] = Field(default_factory=list)


class ClusterStat(BaseModel):
    cluster_id: int
    importance_score: float
    post_count: int
    avg_score: float
    avg_comments: float
    avg_upvote_ratio: float


class WeekResult(BaseModel):
    niche: str | None = None
    week_number: int
    week_label: str
    post_count: int
    clusters_found: int = 0
    noise_posts: int = 0
    trends: list[Trend] = Field(default_factory=list)
    cluster_stats: list[ClusterStat] = Field(default_factory=list)


class NicheSummary(BaseModel):
    niche: str
    total_posts: int
    weeks_available: list[int]
    total_trends: int


class TrendResponse(BaseModel):
    niche: str
    week: int | None = None
    results: list[WeekResult]


class AllNichesSummary(BaseModel):
    generated_at: str
    model: str
    niches: list[NicheSummary]


class HealthResponse(BaseModel):
    status: str
    database: str
    trends_loaded: bool
    niches: list[str]
