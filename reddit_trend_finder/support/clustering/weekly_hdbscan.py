"""
weekly_hdbscan.py — HDBSCAN clustering with UMAP dimensionality reduction.

Key advantages over K-Means:
  • No need to pre-specify k (number of clusters).
  • Automatically discovers noise points (label = -1).
  • Provides membership probabilities — used downstream to select
    "core" posts that best represent each cluster.
"""

import os
import sys

# Add parent directory (support/) to path so we can import config
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pandas as pd
import hdbscan
import umap

from config import (
    HDBSCAN_MIN_CLUSTER_SIZE,
    HDBSCAN_MIN_SAMPLES,
    HDBSCAN_METRIC,
    UMAP_N_COMPONENTS,
    UMAP_N_NEIGHBORS,
    UMAP_MIN_DIST,
    UMAP_METRIC,
    W_SCORE,
    W_COMMENTS,
    W_UPVOTE,
    TOP_N_CLUSTERS,
    TOP_POSTS_PER_CLUSTER,
)


# ────────────────────────────────────────────────────────────
# UMAP + HDBSCAN
# ────────────────────────────────────────────────────────────

def reduce_dimensions(embeddings: np.ndarray) -> np.ndarray:
    """
    Reduce 384-d embeddings to a lower-dimensional space with UMAP
    so HDBSCAN can work more effectively in a denser manifold.
    """
    n_samples = len(embeddings)
    n_neighbors = min(UMAP_N_NEIGHBORS, n_samples - 1)
    n_components = min(UMAP_N_COMPONENTS, n_samples - 2, embeddings.shape[1])

    reducer = umap.UMAP(
        n_components=n_components,
        n_neighbors=n_neighbors,
        min_dist=UMAP_MIN_DIST,
        metric=UMAP_METRIC,
        random_state=42,
    )
    return reducer.fit_transform(embeddings)


def cluster_embeddings(
    embeddings: np.ndarray,
    min_cluster_size: int = HDBSCAN_MIN_CLUSTER_SIZE,
    min_samples: int = HDBSCAN_MIN_SAMPLES,
):
    """
    Run HDBSCAN on (optionally UMAP-reduced) embeddings.

    Returns
    -------
    labels : np.ndarray          cluster labels (-1 = noise)
    probabilities : np.ndarray   membership probability per point
    clusterer : hdbscan.HDBSCAN  fitted object (for inspection)
    """
    # Reduce if high-dimensional
    if embeddings.shape[1] > 20:
        reduced = reduce_dimensions(embeddings)
    else:
        reduced = embeddings

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric=HDBSCAN_METRIC,
        cluster_selection_method="eom",
        prediction_data=True,
    )
    labels = clusterer.fit_predict(reduced)
    probabilities = clusterer.probabilities_

    return labels, probabilities, clusterer


# ────────────────────────────────────────────────────────────
# SCORING & RANKING
# ────────────────────────────────────────────────────────────

def score_clusters(df: pd.DataFrame, top_n: int = TOP_N_CLUSTERS) -> tuple:
    """
    Score each cluster by a weighted engagement metric.

    importance = avg_score * W_SCORE
               + avg_comments * W_COMMENTS
               + avg_upvote_ratio * 100 * W_UPVOTE

    Parameters
    ----------
    df : DataFrame with columns [cluster, score, num_comments, upvote_ratio]
    top_n : how many clusters to return

    Returns
    -------
    stats_df  : DataFrame with per-cluster stats, sorted by importance
    top_ids   : list of top cluster IDs
    """
    rows = []
    for cluster_id, grp in df[df["cluster"] != -1].groupby("cluster"):
        importance = (
            grp["score"].mean() * W_SCORE
            + grp["num_comments"].mean() * W_COMMENTS
            + grp["upvote_ratio"].mean() * 100 * W_UPVOTE
        )
        rows.append(
            {
                "cluster_id": cluster_id,
                "importance_score": round(importance, 2),
                "post_count": len(grp),
                "avg_score": round(grp["score"].mean(), 1),
                "avg_comments": round(grp["num_comments"].mean(), 1),
                "avg_upvote_ratio": round(grp["upvote_ratio"].mean(), 3),
            }
        )

    stats_df = pd.DataFrame(rows).sort_values("importance_score", ascending=False)
    top_ids = stats_df.head(top_n)["cluster_id"].tolist()
    return stats_df, top_ids


# ────────────────────────────────────────────────────────────
# PROBABILITY-AWARE POST SELECTION
# ────────────────────────────────────────────────────────────

def select_top_posts(
    df_cluster: pd.DataFrame,
    top_n: int = TOP_POSTS_PER_CLUSTER,
) -> pd.DataFrame:
    """
    Select the best posts from a single cluster using a combined rank of:
      60 % HDBSCAN probability  (core representativeness)
      40 % engagement score     (community interest)

    This ensures the LLM sees posts that are both *central* to the
    cluster topic and *popular* with the community.
    """
    tmp = df_cluster.copy()

    # Rank by probability (higher = better → ascending rank)
    tmp["prob_rank"] = tmp["probability"].rank(ascending=False, method="min")

    # Engagement composite for ranking
    tmp["engagement"] = (
        tmp["score"] * W_SCORE
        + tmp["num_comments"] * W_COMMENTS
        + tmp["upvote_ratio"] * 100 * W_UPVOTE
    )
    tmp["eng_rank"] = tmp["engagement"].rank(ascending=False, method="min")

    # Combined rank (lower = better)
    tmp["combined_rank"] = tmp["prob_rank"] * 0.6 + tmp["eng_rank"] * 0.4

    return tmp.nsmallest(top_n, "combined_rank")
