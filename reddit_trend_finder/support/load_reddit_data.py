"""
load_reddit_data.py - Load preprocessed Reddit data into database

Run this AFTER setup_database.py
"""

import pandas as pd
from database_util import connect_database, insert_posts_from_df, table_stats
from config import RAW_CSV_PATH

def main():
    # Load your preprocessed CSV
    print(f"📂 Loading CSV from {RAW_CSV_PATH}...")
    df = pd.read_csv(RAW_CSV_PATH)
    
    print(f"✅ Loaded {len(df):,} posts")
    print(f"📊 Niches: {df['niche'].unique()}")
    
    # Connect to database
    conn = connect_database()
    
    # Insert posts
    print("\n📥 Inserting posts into database...")
    insert_posts_from_df(conn, df)
    
    # Show stats
    table_stats(conn)
    
    conn.close()
    print("\n✅ Data loaded successfully!")

if __name__ == "__main__":
    main()