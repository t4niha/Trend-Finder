"""
compare_clustering.py — Run K-Means, HDBSCAN, GMM, and Agglomerative
on one (niche, week) slice and compare using internal metrics.
"""

import time
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
import hdbscan
import umap

from config import (
    HDBSCAN_MIN_CLUSTER_SIZE, HDBSCAN_MIN_SAMPLES, HDBSCAN_METRIC,
    UMAP_N_COMPONENTS, UMAP_N_NEIGHBORS, UMAP_MIN_DIST, UMAP_METRIC,
)
from database_util import connect_database, get_posts_by_niche, get_embeddings_by_niche

# ── CONFIG ─────────────────────────────────────────────────
NICHE = "technology"
WEEK  = 14          # pick a week with ~250 posts
K     = 12           # number of clusters for K-Means, GMM, Agglomerative


def reduce(embeddings):
    reducer = umap.UMAP(
        n_components=UMAP_N_COMPONENTS,
        n_neighbors=min(UMAP_N_NEIGHBORS, len(embeddings) - 1),
        min_dist=UMAP_MIN_DIST,
        metric=UMAP_METRIC,
        random_state=42,
    )
    return reducer.fit_transform(embeddings)


def evaluate(X, labels, name, elapsed, n_noise=0):
    """Compute metrics, excluding noise points (label=-1) for fair comparison."""
    mask = labels != -1
    X_clean = X[mask]
    labels_clean = labels[mask]

    n_clusters = len(set(labels_clean))

    if n_clusters < 2:
        print(f"  {name}: only {n_clusters} cluster(s) — metrics undefined.")
        return None

    sil = silhouette_score(X_clean, labels_clean)
    ch  = calinski_harabasz_score(X_clean, labels_clean)
    db  = davies_bouldin_score(X_clean, labels_clean)

    return {
        "Algorithm": name,
        "Clusters": n_clusters,
        "Noise Points": n_noise,
        "Silhouette": round(sil, 4),
        "Calinski-Harabasz": round(ch, 2),
        "Davies-Bouldin": round(db, 4),
        "Time (s)": round(elapsed, 2),
        "Requires k?": "No" if name == "HDBSCAN" else "Yes",
    }


def main():
    # ── Load data ──────────────────────────────────────────
    conn = connect_database()
    df = get_posts_by_niche(conn, NICHE)
    post_ids, embeddings = get_embeddings_by_niche(conn, NICHE)
    conn.close()

    if embeddings.ndim == 1:
        embeddings = np.array([np.fromstring(str(e).strip("[]"), sep=",") for e in embeddings])

    # Align
    emb_map = dict(zip(post_ids, range(len(post_ids))))
    df = df[df["post_id"].isin(emb_map)].copy()
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"])
    df["week_number"] = df["timestamp_utc"].dt.isocalendar().week.astype(int)

    mask = df["week_number"] == WEEK
    df_w = df[mask].reset_index(drop=True)
    indices = [emb_map[pid] for pid in df_w["post_id"]]
    raw_emb = embeddings[indices]

    print(f"\nNiche: {NICHE}  |  Week: {WEEK}  |  Posts: {len(df_w)}")
    print(f"Reducing {raw_emb.shape[1]}-d → {UMAP_N_COMPONENTS}-d with UMAP...\n")

    X = reduce(raw_emb)

    results = []

    # ── 1. K-Means ─────────────────────────────────────────
    t0 = time.time()
    km = KMeans(n_clusters=K, random_state=42, n_init=10)
    km_labels = km.fit_predict(X)
    t1 = time.time()
    r = evaluate(X, km_labels, "K-Means", t1 - t0)
    if r: results.append(r)

    # ── 2. HDBSCAN ─────────────────────────────────────────
    t0 = time.time()
    hdb = hdbscan.HDBSCAN(
        min_cluster_size=HDBSCAN_MIN_CLUSTER_SIZE,
        min_samples=HDBSCAN_MIN_SAMPLES,
        metric=HDBSCAN_METRIC,
        cluster_selection_method="eom",
    )
    hdb_labels = hdb.fit_predict(X)
    t1 = time.time()
    n_noise = (hdb_labels == -1).sum()
    r = evaluate(X, hdb_labels, "HDBSCAN", t1 - t0, n_noise=n_noise)
    if r: results.append(r)

    # ── 3. GMM ─────────────────────────────────────────────
    t0 = time.time()
    gmm = GaussianMixture(n_components=K, random_state=42, covariance_type="full")
    gmm_labels = gmm.fit_predict(X)
    t1 = time.time()
    r = evaluate(X, gmm_labels, "GMM", t1 - t0)
    if r: results.append(r)

    # ── 4. Agglomerative ───────────────────────────────────
    t0 = time.time()
    agg = AgglomerativeClustering(n_clusters=K, linkage="ward")
    agg_labels = agg.fit_predict(X)
    t1 = time.time()
    r = evaluate(X, agg_labels, "Agglomerative", t1 - t0)
    if r: results.append(r)

    # ── Print table ────────────────────────────────────────
    table = pd.DataFrame(results)
    print("\n" + "=" * 90)
    print(f"  CLUSTERING COMPARISON — r/{NICHE}, Week {WEEK} ({len(df_w)} posts)")
    print("=" * 90)
    print(table.to_string(index=False))
    print("=" * 90)

    # Save
    table.to_csv("clustering_comparison.csv", index=False)
    print(f"\nSaved to clustering_comparison.csv\n")


if __name__ == "__main__":
    main()