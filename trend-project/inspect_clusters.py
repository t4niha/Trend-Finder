import pandas as pd

df = pd.read_csv("reddit_agglomerative_clusters.csv")

# show 5 posts from each cluster
for cluster_id in sorted(df["agglomerative_cluster"].unique()):
    print("\n======================")
    print("CLUSTER:", cluster_id)
    print("======================")

    sample = df[df["agglomerative_cluster"] == cluster_id]["text_translated"].head(5)

    for text in sample:
        print("-", text[:100])