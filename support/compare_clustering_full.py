"""
compare_clustering_full.py — Run K-Means, HDBSCAN, GMM, and Agglomerative
on the FULL dataset (~7,090 posts, all niches, all weeks) with K=6
matching the 6 niches.

Since we have ground truth labels (the niche each post belongs to),
we can also compute EXTERNAL metrics (ARI, NMI) alongside internal ones.

Usage:
    cd support
    python compare_clustering_full.py
"""

import time
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.mixture import GaussianMixture
from sklearn.metrics import (
    silhouette_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    adjusted_rand_score,
    normalized_mutual_info_score,
)
from sklearn.preprocessing import LabelEncoder
import hdbscan
import umap

from config import (
    HDBSCAN_MIN_CLUSTER_SIZE, HDBSCAN_MIN_SAMPLES, HDBSCAN_METRIC,
    UMAP_N_COMPONENTS, UMAP_N_NEIGHBORS, UMAP_MIN_DIST, UMAP_METRIC,
    NICHES,
)
from database_util import connect_database, get_posts_by_niche, get_embeddings_by_niche

# ── CONFIG ─────────────────────────────────────────────────
K = 6  # number of niches


def reduce(embeddings):
    n = len(embeddings)
    reducer = umap.UMAP(
        n_components=UMAP_N_COMPONENTS,
        n_neighbors=min(UMAP_N_NEIGHBORS, n - 1),
        min_dist=UMAP_MIN_DIST,
        metric=UMAP_METRIC,
        random_state=42,
    )
    return reducer.fit_transform(embeddings)


def evaluate(X, labels, true_labels, name, elapsed, n_noise=0):
    """
    Compute internal + external metrics.
    Noise points (label=-1) are excluded for fair comparison.
    """
    mask = labels != -1
    X_clean = X[mask]
    labels_clean = labels[mask]
    true_clean = true_labels[mask]

    n_clusters = len(set(labels_clean))
    coverage = mask.sum() / len(labels) * 100

    if n_clusters < 2:
        print(f"  {name}: only {n_clusters} cluster(s) — metrics undefined.")
        return None

    # Internal metrics (no ground truth needed)
    sil = silhouette_score(X_clean, labels_clean)
    ch  = calinski_harabasz_score(X_clean, labels_clean)
    db  = davies_bouldin_score(X_clean, labels_clean)

    # External metrics (compare against niche labels)
    ari = adjusted_rand_score(true_clean, labels_clean)
    nmi = normalized_mutual_info_score(true_clean, labels_clean)

    return {
        "Algorithm": name,
        "Clusters": n_clusters,
        "Noise": n_noise,
        "Coverage": f"{coverage:.1f}%",
        "Silhouette": round(sil, 4),
        "Calinski-Harabasz": round(ch, 2),
        "Davies-Bouldin": round(db, 4),
        "ARI": round(ari, 4),
        "NMI": round(nmi, 4),
        "Time (s)": round(elapsed, 2),
    }


def main():
    conn = connect_database()

    # ── Load ALL niches ────────────────────────────────────
    all_dfs = []
    all_embs = []

    for niche in NICHES:
        df = get_posts_by_niche(conn, niche)
        post_ids, embeddings = get_embeddings_by_niche(conn, niche)

        if post_ids is None or len(post_ids) == 0:
            print(f"  ⚠️  No embeddings for {niche} — skipping.")
            continue

        if embeddings.ndim == 1:
            embeddings = np.array([np.fromstring(str(e).strip("[]"), sep=",") for e in embeddings])

        emb_map = dict(zip(post_ids, range(len(post_ids))))
        df = df[df["post_id"].isin(emb_map)].copy()
        indices = [emb_map[pid] for pid in df["post_id"]]
        emb_matrix = embeddings[indices]

        all_dfs.append(df)
        all_embs.append(emb_matrix)
        print(f"  Loaded r/{niche}: {len(df):,} posts")

    conn.close()

    df_all = pd.concat(all_dfs, ignore_index=True)
    X_raw = np.vstack(all_embs)

    # Encode niche labels as integers for external metrics
    le = LabelEncoder()
    true_labels = le.fit_transform(df_all["niche"].values)

    print(f"\n{'=' * 90}")
    print(f"  FULL DATASET: {len(df_all):,} posts  |  {len(NICHES)} niches  |  K = {K}")
    print(f"  Niches: {list(le.classes_)}")
    print(f"{'=' * 90}")

    # ── UMAP reduction ─────────────────────────────────────
    print(f"\n  Reducing {X_raw.shape[1]}-d → {UMAP_N_COMPONENTS}-d with UMAP...")
    t0 = time.time()
    X = reduce(X_raw)
    umap_time = time.time() - t0
    print(f"  UMAP done in {umap_time:.1f}s\n")

    results = []

    # ── 1. K-Means ─────────────────────────────────────────
    print("  Running K-Means...")
    t0 = time.time()
    km = KMeans(n_clusters=K, random_state=42, n_init=10)
    km_labels = km.fit_predict(X)
    elapsed = time.time() - t0
    r = evaluate(X, km_labels, true_labels, "K-Means", elapsed)
    if r: results.append(r)

    # ── 2. HDBSCAN ─────────────────────────────────────────
    print("  Running HDBSCAN...")
    t0 = time.time()
    hdb = hdbscan.HDBSCAN(
        min_cluster_size=HDBSCAN_MIN_CLUSTER_SIZE,
        min_samples=HDBSCAN_MIN_SAMPLES,
        metric=HDBSCAN_METRIC,
        cluster_selection_method="eom",
    )
    hdb_labels = hdb.fit_predict(X)
    elapsed = time.time() - t0
    n_noise = (hdb_labels == -1).sum()
    r = evaluate(X, hdb_labels, true_labels, "HDBSCAN", elapsed, n_noise=n_noise)
    if r: results.append(r)

    # ── 3. GMM ─────────────────────────────────────────────
    print("  Running GMM...")
    t0 = time.time()
    gmm = GaussianMixture(n_components=K, random_state=42, covariance_type="full")
    gmm_labels = gmm.fit_predict(X)
    elapsed = time.time() - t0
    r = evaluate(X, gmm_labels, true_labels, "GMM", elapsed)
    if r: results.append(r)

    # ── 4. Agglomerative ───────────────────────────────────
    print("  Running Agglomerative...")
    t0 = time.time()
    agg = AgglomerativeClustering(n_clusters=K, linkage="ward")
    agg_labels = agg.fit_predict(X)
    elapsed = time.time() - t0
    r = evaluate(X, agg_labels, true_labels, "Agglomerative", elapsed)
    if r: results.append(r)

    # ── Print results ──────────────────────────────────────
    table = pd.DataFrame(results)

    print(f"\n{'=' * 110}")
    print(f"  CLUSTERING COMPARISON — Full Dataset ({len(df_all):,} posts, K={K})")
    print(f"{'=' * 110}")
    print(table.to_string(index=False))
    print(f"{'=' * 110}")

    print("\n  Metric Guide:")
    print("    Silhouette     (-1 to +1, higher = better separated clusters)")
    print("    Calinski-Harabasz  (higher = better, ratio of between/within variance)")
    print("    Davies-Bouldin     (lower = better, less cluster overlap)")
    print("    ARI            (-1 to +1, higher = better match to true niche labels)")
    print("    NMI            (0 to 1, higher = better match to true niche labels)")
    print("    Coverage       (% of posts assigned to a cluster, not noise)")

    # Save
    table.to_csv("clustering_comparison_full.csv", index=False)
    print(f"\n  Saved to clustering_comparison_full.csv\n")


if __name__ == "__main__":
    main()