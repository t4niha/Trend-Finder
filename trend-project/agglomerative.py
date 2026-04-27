import numpy as np
import pandas as pd

from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import silhouette_score

print("LOADING DATA...")

# Load Reddit dataset
df = pd.read_csv("final_trendingtopics_reddit.csv")

# Load sentence embeddings
embeddings = np.load("sentence_embeddings.npy")

print("DATA SHAPE:", df.shape)
print("EMBEDDINGS SHAPE:", embeddings.shape)

print("RUNNING AGGLOMERATIVE CLUSTERING...")

# Create Agglomerative Clustering model
model = AgglomerativeClustering(
    n_clusters=10,
    metric="cosine",
    linkage="average"
)

# Fit model and get cluster labels
labels = model.fit_predict(embeddings)

# Add cluster labels to dataframe
df["agglomerative_cluster"] = labels

# Calculate silhouette score
print("CALCULATING SILHOUETTE SCORE...")
silhouette = silhouette_score(embeddings, labels, metric="cosine")

# Save outputs
df.to_csv("reddit_agglomerative_clusters.csv", index=False)
np.save("agglomerative_labels.npy", labels)

print("DONE")
print("Saved: reddit_agglomerative_clusters.csv")
print("Saved: agglomerative_labels.npy")
print("Number of clusters:", len(set(labels)))
print("Silhouette Score:", silhouette)