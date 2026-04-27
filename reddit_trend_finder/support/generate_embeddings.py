"""
generate_embeddings.py - Generate embeddings and store in database

Run this AFTER load_reddit_data.py
"""

import numpy as np
from sentence_transformers import SentenceTransformer
from database_util import (
    connect_database, 
    get_posts_by_niche, 
    insert_embeddings,
    table_stats
)
from tqdm import tqdm

NICHES = ['technology', 'science', 'worldnews', 'gaming', 'smartphones', 'movies']
MODEL_NAME = 'all-MiniLM-L6-v2'

def main():
    # Load model
    print(f"🤖 Loading embedding model: {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)
    print("✅ Model loaded\n")
    
    # Connect to database
    conn = connect_database()
    
    # Process each niche
    for niche in NICHES:
        print(f"\n{'='*60}")
        print(f"Processing: {niche}")
        print('='*60)
        
        # Get posts
        df = get_posts_by_niche(conn, niche)
        print(f"📊 Posts: {len(df):,}")
        
        if len(df) == 0:
            print(f"⚠️  No posts found for {niche}")
            continue
        
        # Generate embeddings
        print(f"🔄 Generating embeddings...")
        texts = df['text_translated'].fillna(df['full_text']).tolist()
        embeddings = model.encode(
            texts,
            show_progress_bar=True,
            batch_size=32,
            convert_to_numpy=True
        )
        
        # Store in database
        print(f"💾 Storing embeddings...")
        insert_embeddings(conn, df['post_id'].tolist(), embeddings, niche)
    
    # Show final stats
    print(f"\n{'='*60}")
    table_stats(conn)
    
    conn.close()
    print("✅ All embeddings generated and stored!\n")

if __name__ == "__main__":
    main()