"""
main.py — Reddit Trend Finder pipeline (console runner).

Usage:
    python main.py                       # all niches, all weeks
    python main.py --niche technology    # single niche
    python main.py --week 14             # single week number

Workflow:
  1. Connect to PostgreSQL and fetch posts + embeddings per niche.
  2. Assign ISO week numbers.
  3. For each (niche, week) slice:
       a. UMAP → HDBSCAN clustering.
       b. Score clusters by weighted engagement.
       c. Select top 3 clusters; pick top 8 posts per cluster
          (probability-aware ranking).
       d. Send to Gemini → structured JSON trend output.
  4. Save all results to output/weekly_trends.json.
"""

import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd

# Project imports
from support.config import (
    NICHES,
    TOP_N_CLUSTERS,
    TOP_POSTS_PER_CLUSTER,
    OUTPUT_DIR,
    OUTPUT_FILE,
    GEMINI_MODEL,
)
from support.database_util import connect_database, get_posts_by_niche, get_embeddings_by_niche

from support.clustering.weekly_hdbscan import (
    cluster_embeddings,
    score_clusters,
    select_top_posts,
)
from support.clustering.gemini_trends import (
    build_cluster_context,
    build_prompt,
    call_gemini,
    parse_gemini_response,
)


# ────────────────────────────────────────────────────────────
# HELPERS
# ────────────────────────────────────────────────────────────

def _week_label(week_df: pd.DataFrame, week_num: int) -> str:
    """Human-readable label like 'Mar 25 – Mar 31, 2026'."""
    start = week_df["timestamp_utc"].min().strftime("%b %d")
    end = week_df["timestamp_utc"].max().strftime("%b %d, %Y")
    return f"{start} – {end}"


def process_niche_week(
    df_week: pd.DataFrame,
    embeddings_week: np.ndarray,
    niche: str,
    week_num: int,
    week_lbl: str,
) -> dict | None:
    """
    Run the full clustering → scoring → LLM pipeline for one (niche, week).
    Returns a result dict or None on failure.
    """
    n = len(df_week)

    # ── 1. Cluster ─────────────────────────────────────────
    labels, probabilities, _ = cluster_embeddings(embeddings_week)
    df_week = df_week.copy()
    df_week["cluster"] = labels
    df_week["probability"] = probabilities

    n_clusters = len(set(labels) - {-1})
    n_noise = (labels == -1).sum()
    print(f"    Clusters found : {n_clusters}  |  Noise posts: {n_noise}")

    if n_clusters == 0:
        print("    ⚠️  No clusters found — skipping.")
        return None

    # ── 2. Score & rank clusters ───────────────────────────
    stats_df, top_ids = score_clusters(df_week, top_n=TOP_N_CLUSTERS)
    print(f"    Top {len(top_ids)} clusters: {top_ids}")

    # ── 3. Build LLM context ──────────────────────────────
    cluster_contexts = []
    for cid in top_ids:
        grp = df_week[df_week["cluster"] == cid]
        top_posts = select_top_posts(grp, top_n=TOP_POSTS_PER_CLUSTER)
        ctx = build_cluster_context(grp, cid, top_posts)
        cluster_contexts.append(ctx)

    prompt = build_prompt(niche, cluster_contexts, week_label=week_lbl)

    # ── 4. Call Gemini ─────────────────────────────────────
    print(f"    Calling Gemini ({GEMINI_MODEL})...")
    raw = call_gemini(prompt)
    result = parse_gemini_response(raw)

    if result is None:
        print("    ❌ Failed to parse Gemini response.")
        return None

    # Attach metadata
    result["week_number"] = int(week_num)
    result["week_label"] = week_lbl
    result["post_count"] = n
    result["clusters_found"] = n_clusters
    result["noise_posts"] = int(n_noise)
    result["cluster_stats"] = stats_df.to_dict(orient="records")

    titles = [f"#{t['rank']} {t['title']}" for t in result.get("trends", [])]
    print(f"    ✅ Trends: {' | '.join(titles)}")

    return result


# ────────────────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Reddit Trend Finder — weekly HDBSCAN + Gemini")
    parser.add_argument("--niche", type=str, default=None, help="Single niche to process")
    parser.add_argument("--week", type=int, default=None, help="Single ISO week number to process")
    args = parser.parse_args()

    niches = [args.niche] if args.niche else NICHES

    print("\n" + "=" * 70)
    print("  🔍 REDDIT TREND FINDER — Weekly HDBSCAN + Gemini Pipeline")
    print("=" * 70)
    print(f"  Niches  : {niches}")
    print(f"  Model   : {GEMINI_MODEL}")
    print(f"  Output  : {OUTPUT_FILE}")
    print("=" * 70 + "\n")

    conn = connect_database()

    all_results: dict[str, list] = {}

    for niche in niches:
        print(f"\n{'━' * 70}")
        print(f"  📡 Niche: r/{niche}")
        print(f"{'━' * 70}")

        # Fetch posts
        df = get_posts_by_niche(conn, niche)
        if df.empty:
            print(f"  ⚠️  No posts found for r/{niche} — skipping.")
            continue

        # Fetch embeddings
        post_ids_emb, embeddings = get_embeddings_by_niche(conn, niche)
        if post_ids_emb is None or len(post_ids_emb) == 0:
            print(f"  ⚠️  No embeddings found for r/{niche} — skipping.")
            continue

        # Parse string representations from pgvector if needed
        if embeddings.ndim == 1:
            embeddings = np.array([np.fromstring(str(e).strip('[]'), sep=',') for e in embeddings])

        # Align embeddings with posts
        emb_map = dict(zip(post_ids_emb, range(len(post_ids_emb))))
        df = df[df["post_id"].isin(emb_map)].copy()
        emb_indices = [emb_map[pid] for pid in df["post_id"]]
        emb_matrix = embeddings[emb_indices]

        # Numeric cleanup
        for col in ["score", "num_comments", "upvote_ratio"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        # Parse weeks
        df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"])
        df["week_number"] = df["timestamp_utc"].dt.isocalendar().week.astype(int)

        weeks = sorted(df["week_number"].unique())
        if args.week is not None:
            weeks = [w for w in weeks if w == args.week]

        print(f"  Posts: {len(df):,}  |  Weeks: {weeks}")

        niche_results = []

        for wnum in weeks:
            mask = df["week_number"] == wnum
            df_w = df[mask].reset_index(drop=True)
            emb_w = emb_matrix[mask.values]

            if len(df_w) < 20:
                print(f"\n  📅 Week {wnum}: only {len(df_w)} posts — skipping.")
                continue

            wlbl = _week_label(df_w, wnum)
            print(f"\n  📅 {wlbl} ({len(df_w):,} posts)")

            result = process_niche_week(df_w, emb_w, niche, wnum, wlbl)
            if result:
                niche_results.append(result)

            time.sleep(30)  # Gemini rate-limit buffer

        all_results[niche] = niche_results

    conn.close()

    # ── Save output (merge with existing results) ─────────
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Load existing results if any
    existing = {}
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f).get("results", {})

    # Merge new results into existing
    existing.update(all_results)

    output = {
        "generated_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "model": GEMINI_MODEL,
        "niches_processed": list(existing.keys()),
        "results": existing,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    total_trends = sum(
        len(r.get("trends", []))
        for niche_list in existing.values()
        for r in niche_list
    )


if __name__ == "__main__":
    main()