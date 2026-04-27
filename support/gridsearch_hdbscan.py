"""
gridsearch_hdbscan.py — Hyperparameter optimization for HDBSCAN + UMAP.

Sweeps over combinations of:
  - UMAP n_components (dimensionality)
  - HDBSCAN min_cluster_size
  - HDBSCAN min_samples
  - HDBSCAN cluster_selection_method (eom vs leaf)

Evaluates each combination using:
  - Internal: Silhouette, Calinski-Harabasz, Davies-Bouldin
  - External: ARI, NMI (against true niche labels — full dataset only)
  - Practical: cluster count, noise %, coverage

Modes:
  --mode full     → all ~7K posts, K=6 niches as ground truth
  --mode weekly   → single niche/week (~250 posts), no ground truth

Usage:
    cd support
    python gridsearch_hdbscan.py --mode full
    python gridsearch_hdbscan.py --mode weekly --niche technology --week 14
"""

import argparse
import itertools
import time
import warnings

import numpy as np
import pandas as pd
import hdbscan
import umap
from sklearn.metrics import (
    silhouette_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    adjusted_rand_score,
    normalized_mutual_info_score,
)
from sklearn.preprocessing import LabelEncoder

from config import NICHES, UMAP_MIN_DIST, UMAP_METRIC, HDBSCAN_METRIC
from database_util import connect_database, get_posts_by_niche, get_embeddings_by_niche

warnings.filterwarnings("ignore", category=FutureWarning)

# ══════════════════════════════════════════════════════════════
# SEARCH GRID — edit these to control the sweep
# ══════════════════════════════════════════════════════════════

PARAM_GRID = {
    "umap_n_components": [10, 15, 20, 25, 30],
    "min_cluster_size":  [10, 15, 20, 25, 30, 40, 50],
    "min_samples":       [3, 5, 7, 10, 15],
    "cluster_selection_method": ["eom", "leaf"],
}

# Fixed UMAP params
UMAP_N_NEIGHBORS = 15


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def load_full_dataset():
    """Load all niches, return embeddings + niche labels."""
    conn = connect_database()
    all_dfs = []
    all_embs = []

    for niche in NICHES:
        df = get_posts_by_niche(conn, niche)
        post_ids, embeddings = get_embeddings_by_niche(conn, niche)

        if post_ids is None or len(post_ids) == 0:
            continue

        if embeddings.ndim == 1:
            embeddings = np.array([
                np.fromstring(str(e).strip("[]"), sep=",") for e in embeddings
            ])

        emb_map = dict(zip(post_ids, range(len(post_ids))))
        df = df[df["post_id"].isin(emb_map)].copy()
        indices = [emb_map[pid] for pid in df["post_id"]]

        all_dfs.append(df)
        all_embs.append(embeddings[indices])

    conn.close()

    df_all = pd.concat(all_dfs, ignore_index=True)
    X_raw = np.vstack(all_embs)

    le = LabelEncoder()
    true_labels = le.fit_transform(df_all["niche"].values)

    return X_raw, true_labels, df_all


def load_weekly_dataset(niche, week):
    """Load a single niche/week slice."""
    conn = connect_database()
    df = get_posts_by_niche(conn, niche)
    post_ids, embeddings = get_embeddings_by_niche(conn, niche)
    conn.close()

    if embeddings.ndim == 1:
        embeddings = np.array([
            np.fromstring(str(e).strip("[]"), sep=",") for e in embeddings
        ])

    emb_map = dict(zip(post_ids, range(len(post_ids))))
    df = df[df["post_id"].isin(emb_map)].copy()
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"])
    df["week_number"] = df["timestamp_utc"].dt.isocalendar().week.astype(int)

    mask = df["week_number"] == week
    df_w = df[mask].reset_index(drop=True)
    indices = [emb_map[pid] for pid in df_w["post_id"]]
    X_raw = embeddings[indices]

    return X_raw, None, df_w


def run_umap(X_raw, n_components):
    """UMAP reduction with caching per n_components."""
    n = len(X_raw)
    reducer = umap.UMAP(
        n_components=n_components,
        n_neighbors=min(UMAP_N_NEIGHBORS, n - 1),
        min_dist=UMAP_MIN_DIST,
        metric=UMAP_METRIC,
        random_state=42,
    )
    return reducer.fit_transform(X_raw)


def evaluate_single(X, labels, true_labels=None):
    """Evaluate one clustering result. Returns a dict of metrics."""
    mask = labels != -1
    X_clean = X[mask]
    labels_clean = labels[mask]

    n_clusters = len(set(labels_clean))
    n_noise = (~mask).sum()
    coverage = mask.sum() / len(labels) * 100

    if n_clusters < 2:
        return None

    result = {
        "n_clusters": n_clusters,
        "noise": n_noise,
        "noise_pct": round(n_noise / len(labels) * 100, 1),
        "coverage": round(coverage, 1),
        "silhouette": round(silhouette_score(X_clean, labels_clean), 4),
        "calinski_harabasz": round(calinski_harabasz_score(X_clean, labels_clean), 2),
        "davies_bouldin": round(davies_bouldin_score(X_clean, labels_clean), 4),
    }

    # External metrics if ground truth available
    if true_labels is not None:
        true_clean = true_labels[mask]
        result["ari"] = round(adjusted_rand_score(true_clean, labels_clean), 4)
        result["nmi"] = round(normalized_mutual_info_score(true_clean, labels_clean), 4)

    return result


# ══════════════════════════════════════════════════════════════
# GRID SEARCH
# ══════════════════════════════════════════════════════════════

def grid_search(X_raw, true_labels=None):
    """
    Run HDBSCAN with every parameter combination in PARAM_GRID.
    UMAP results are cached per n_components to avoid redundant computation.
    """
    combos = list(itertools.product(
        PARAM_GRID["umap_n_components"],
        PARAM_GRID["min_cluster_size"],
        PARAM_GRID["min_samples"],
        PARAM_GRID["cluster_selection_method"],
    ))

    total = len(combos)
    print(f"\n  Total combinations: {total}")
    print(f"  UMAP dims: {PARAM_GRID['umap_n_components']}")
    print(f"  min_cluster_size: {PARAM_GRID['min_cluster_size']}")
    print(f"  min_samples: {PARAM_GRID['min_samples']}")
    print(f"  selection_method: {PARAM_GRID['cluster_selection_method']}")
    print()

    # Cache UMAP results per n_components
    umap_cache = {}
    results = []
    failed = 0

    for i, (n_comp, mcs, ms, csm) in enumerate(combos, 1):
        # UMAP (cached)
        if n_comp not in umap_cache:
            print(f"  Computing UMAP (n_components={n_comp})...")
            umap_cache[n_comp] = run_umap(X_raw, n_comp)

        X = umap_cache[n_comp]

        # HDBSCAN
        t0 = time.time()
        try:
            clusterer = hdbscan.HDBSCAN(
                min_cluster_size=mcs,
                min_samples=ms,
                metric=HDBSCAN_METRIC,
                cluster_selection_method=csm,
            )
            labels = clusterer.fit_predict(X)
        except Exception as e:
            failed += 1
            continue
        elapsed = time.time() - t0

        # Evaluate
        metrics = evaluate_single(X, labels, true_labels)
        if metrics is None:
            failed += 1
            continue

        metrics.update({
            "umap_n_components": n_comp,
            "min_cluster_size": mcs,
            "min_samples": ms,
            "cluster_selection_method": csm,
            "time": round(elapsed, 3),
        })
        results.append(metrics)

        # Progress
        if i % 50 == 0 or i == total:
            print(f"  [{i}/{total}] completed  |  valid: {len(results)}  |  failed: {failed}")

    return pd.DataFrame(results)


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="HDBSCAN hyperparameter grid search")
    parser.add_argument("--mode", choices=["full", "weekly"], default="full")
    parser.add_argument("--niche", type=str, default="technology")
    parser.add_argument("--week", type=int, default=14)
    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("  HDBSCAN HYPERPARAMETER GRID SEARCH")
    print("=" * 80)

    # Load data
    if args.mode == "full":
        print(f"\n  Mode: FULL DATASET (all niches)")
        X_raw, true_labels, df = load_full_dataset()
    else:
        print(f"\n  Mode: WEEKLY — r/{args.niche}, week {args.week}")
        X_raw, true_labels, df = load_weekly_dataset(args.niche, args.week)

    print(f"  Posts: {len(df):,}  |  Embedding dim: {X_raw.shape[1]}")

    # Run grid search
    t_start = time.time()
    results_df = grid_search(X_raw, true_labels)
    total_time = time.time() - t_start

    if results_df.empty:
        print("\n  ❌ No valid results. Try relaxing the parameter grid.")
        return

    # ── Sort by composite score ────────────────────────────
    # Normalize metrics to 0-1 range and compute weighted composite
    df_scored = results_df.copy()

    # Silhouette: higher = better (already -1 to 1)
    sil_min, sil_max = df_scored["silhouette"].min(), df_scored["silhouette"].max()
    if sil_max > sil_min:
        df_scored["sil_norm"] = (df_scored["silhouette"] - sil_min) / (sil_max - sil_min)
    else:
        df_scored["sil_norm"] = 0.5

    # Davies-Bouldin: lower = better → invert
    db_min, db_max = df_scored["davies_bouldin"].min(), df_scored["davies_bouldin"].max()
    if db_max > db_min:
        df_scored["db_norm"] = 1 - (df_scored["davies_bouldin"] - db_min) / (db_max - db_min)
    else:
        df_scored["db_norm"] = 0.5

    # Calinski-Harabasz: higher = better
    ch_min, ch_max = df_scored["calinski_harabasz"].min(), df_scored["calinski_harabasz"].max()
    if ch_max > ch_min:
        df_scored["ch_norm"] = (df_scored["calinski_harabasz"] - ch_min) / (ch_max - ch_min)
    else:
        df_scored["ch_norm"] = 0.5

    # Composite: weighted sum of normalized internal metrics
    df_scored["composite"] = (
        df_scored["sil_norm"] * 0.4
        + df_scored["db_norm"] * 0.3
        + df_scored["ch_norm"] * 0.3
    )

    # If external metrics available, add them to composite
    if "ari" in df_scored.columns:
        ari_min, ari_max = df_scored["ari"].min(), df_scored["ari"].max()
        if ari_max > ari_min:
            df_scored["ari_norm"] = (df_scored["ari"] - ari_min) / (ari_max - ari_min)
        else:
            df_scored["ari_norm"] = 0.5

        nmi_min, nmi_max = df_scored["nmi"].min(), df_scored["nmi"].max()
        if nmi_max > nmi_min:
            df_scored["nmi_norm"] = (df_scored["nmi"] - nmi_min) / (nmi_max - nmi_min)
        else:
            df_scored["nmi_norm"] = 0.5

        # Reweight: 30% silhouette, 20% DB, 20% CH, 15% ARI, 15% NMI
        df_scored["composite"] = (
            df_scored["sil_norm"] * 0.30
            + df_scored["db_norm"] * 0.20
            + df_scored["ch_norm"] * 0.20
            + df_scored["ari_norm"] * 0.15
            + df_scored["nmi_norm"] * 0.15
        )

    df_scored = df_scored.sort_values("composite", ascending=False).reset_index(drop=True)

    # ── Display top 15 ─────────────────────────────────────
    display_cols = [
        "umap_n_components", "min_cluster_size", "min_samples",
        "cluster_selection_method", "n_clusters", "noise_pct",
        "silhouette", "calinski_harabasz", "davies_bouldin",
    ]
    if "ari" in df_scored.columns:
        display_cols += ["ari", "nmi"]
    display_cols.append("composite")

    print(f"\n{'=' * 120}")
    print(f"  TOP 15 PARAMETER COMBINATIONS (out of {len(df_scored)} valid)")
    print(f"{'=' * 120}")
    print(df_scored[display_cols].head(15).to_string(index=False))
    print(f"{'=' * 120}")

    # ── Best params ────────────────────────────────────────
    best = df_scored.iloc[0]
    print(f"\n  🏆 BEST PARAMETERS:")
    print(f"     UMAP n_components         = {int(best['umap_n_components'])}")
    print(f"     min_cluster_size           = {int(best['min_cluster_size'])}")
    print(f"     min_samples                = {int(best['min_samples'])}")
    print(f"     cluster_selection_method   = {best['cluster_selection_method']}")
    print(f"")
    print(f"     Clusters found             = {int(best['n_clusters'])}")
    print(f"     Noise %                    = {best['noise_pct']}%")
    print(f"     Silhouette                 = {best['silhouette']}")
    print(f"     Calinski-Harabasz          = {best['calinski_harabasz']}")
    print(f"     Davies-Bouldin             = {best['davies_bouldin']}")
    if "ari" in best:
        print(f"     ARI                        = {best['ari']}")
        print(f"     NMI                        = {best['nmi']}")
    print(f"     Composite score            = {best['composite']:.4f}")

    # ── Config suggestion ──────────────────────────────────
    print(f"\n  📋 Copy to config.py:")
    print(f"     UMAP_N_COMPONENTS          = {int(best['umap_n_components'])}")
    print(f"     HDBSCAN_MIN_CLUSTER_SIZE   = {int(best['min_cluster_size'])}")
    print(f"     HDBSCAN_MIN_SAMPLES        = {int(best['min_samples'])}")
    print(f'     # cluster_selection_method  = "{best["cluster_selection_method"]}"')

    # ── Save full results ──────────────────────────────────
    output_file = f"gridsearch_results_{args.mode}.csv"
    df_scored[display_cols].to_csv(output_file, index=False)
    print(f"\n  Saved all {len(df_scored)} results to {output_file}")
    print(f"  Total search time: {total_time:.1f}s")
    print(f"{'=' * 80}\n")


if __name__ == "__main__":
    main()