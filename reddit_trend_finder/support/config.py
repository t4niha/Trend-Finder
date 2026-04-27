"""
config.py — Central configuration for the Reddit Trend Finder pipeline.

All tunable parameters live here. Database credentials are loaded from .env.
"""

import os
from dotenv import load_dotenv

# Load .env from the same directory as this file (support/)
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# ─────────────────────────────────────────────────────────────
# DATABASE (PostgreSQL + pgvector)
# ─────────────────────────────────────────────────────────────
DB_USER     = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = os.getenv("DB_PORT", "5442")
DB_NAME     = os.getenv("DB_NAME", "postgres")

# ─────────────────────────────────────────────────────────────
# GEMINI LLM
# ─────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

# ─────────────────────────────────────────────────────────────
# NICHES
# ─────────────────────────────────────────────────────────────
NICHES = ["technology", "science", "worldnews", "gaming", "smartphones", "movies"]

# ─────────────────────────────────────────────────────────────
# EMBEDDINGS
# ─────────────────────────────────────────────────────────────
EMBEDDING_MODEL   = "all-MiniLM-L6-v2"
EMBEDDING_DIM     = 384
EMBEDDING_BATCH   = 32

# ─────────────────────────────────────────────────────────────
# CLUSTERING (HDBSCAN — weekly)
#
# Rationale:
#   ~250 posts/week in the largest niche (technology).
#   min_cluster_size = 15  →  a cluster needs ≥ 6 % of weekly posts
#   min_samples      = 5   →  lenient core-point definition
#   → Expect 5–10 clusters per week/niche; top 3 selected.
# ─────────────────────────────────────────────────────────────
HDBSCAN_MIN_CLUSTER_SIZE = 10
HDBSCAN_MIN_SAMPLES      = 5
HDBSCAN_METRIC            = "euclidean"

# How many of the best clusters to send to the LLM
TOP_N_CLUSTERS        = 3

# How many posts per cluster are included in the LLM prompt
TOP_POSTS_PER_CLUSTER = 8

# ─────────────────────────────────────────────────────────────
# UMAP (dimensionality reduction before HDBSCAN)
# ─────────────────────────────────────────────────────────────
UMAP_N_COMPONENTS = 10   # 15–30 sweet spot for clustering; 10 is too aggressive
UMAP_N_NEIGHBORS  = 15
UMAP_MIN_DIST     = 0.0
UMAP_METRIC       = "cosine"

# ─────────────────────────────────────────────────────────────
# SCORING WEIGHTS (cluster importance)
#   importance = avg_score*W_SCORE + avg_comments*W_COMMENTS
#                + avg_upvote_ratio*100*W_UPVOTE
# ─────────────────────────────────────────────────────────────
W_SCORE    = 0.5
W_COMMENTS = 0.3
W_UPVOTE   = 0.2

# ─────────────────────────────────────────────────────────────
# OUTPUT (lives inside support/)
# ─────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_DIR   = os.path.join(os.path.dirname(__file__), "output")
OUTPUT_FILE  = os.path.join(OUTPUT_DIR, "weekly_trends.json")

# ─────────────────────────────────────────────────────────────
# FASTAPI
# ─────────────────────────────────────────────────────────────
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://localhost:8080"
).split(",")

# ─────────────────────────────────────────────────────────────
# CSV PATHS (raw / preprocessed data)
# ─────────────────────────────────────────────────────────────
RAW_CSV_PATH = os.getenv(
    "RAW_CSV_PATH",
    os.path.join(PROJECT_ROOT, "data", "final_trendingtopics_reddit.csv"),
)