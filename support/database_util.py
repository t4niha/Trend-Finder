"""
database_util.py - Optimized for Reddit Trend Clustering Project

Tables:
1. posts - Raw Reddit posts
2. embeddings - 384D sentence embeddings (using pgvector)
3. cluster_assignments - Cluster IDs with versioning
4. clusters - Cluster metadata (names, keywords, summaries)
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch
import numpy as np
from config import DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME


# ============================================
# CONNECTION FUNCTIONS
# ============================================

def connect_postgres():
    """Connect to default postgres database"""
    return psycopg2.connect(
        dbname="postgres",  # Connect to default DB first
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )


def create_database(dbname=DB_NAME):
    """Create project database if it doesn't exist"""
    conn = connect_postgres()
    conn.autocommit = True
    cursor = conn.cursor()
    
    cursor.execute(f"SELECT 1 FROM pg_database WHERE datname='{dbname}';")
    exists = cursor.fetchone()
    
    if not exists:
        cursor.execute(f"CREATE DATABASE {dbname};")
        print(f"✅ Database '{dbname}' created")
    else:
        print(f"ℹ️  Database '{dbname}' already exists")
    
    cursor.close()
    conn.close()


def connect_database():
    """Connect to project database"""
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )


# ============================================
# SETUP FUNCTIONS
# ============================================

def enable_pgvector(conn):
    """Enable pgvector extension for storing embeddings"""
    cursor = conn.cursor()
    try:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        conn.commit()
        print("✅ pgvector extension enabled")
    except Exception as e:
        print(f"⚠️  pgvector installation needed: {e}")
        print("   Run: sudo apt-get install postgresql-16-pgvector")
        print("   Or see: https://github.com/pgvector/pgvector")
    finally:
        cursor.close()


def create_all_tables(conn):
    """Create all required tables for the project"""
    cursor = conn.cursor()
    
    # Table 1: Posts (Raw Reddit data)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        post_id VARCHAR(255) PRIMARY KEY,
        niche VARCHAR(50) NOT NULL,
        title TEXT NOT NULL,
        author VARCHAR(255),
        score INTEGER,
        upvote_ratio FLOAT,
        num_comments INTEGER,
        timestamp_utc TIMESTAMP,
        permalink TEXT,
        url TEXT,
        selftext TEXT,
        full_text TEXT,
        text_translated TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    print("✅ Table 'posts' created")
    
    # Table 2: Embeddings (384D vectors using pgvector)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS embeddings (
        id SERIAL PRIMARY KEY,
        post_id VARCHAR(255) UNIQUE NOT NULL,
        niche VARCHAR(50) NOT NULL,
        embedding VECTOR(384),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (post_id) REFERENCES posts(post_id) ON DELETE CASCADE
    );
    """)
    print("✅ Table 'embeddings' created")
    
    # Table 3: Cluster Assignments (versioned)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cluster_assignments (
        id SERIAL PRIMARY KEY,
        post_id VARCHAR(255) NOT NULL,
        niche VARCHAR(50) NOT NULL,
        cluster_id INTEGER,
        cluster_version INTEGER DEFAULT 1,
        is_final BOOLEAN DEFAULT TRUE,
        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (post_id) REFERENCES posts(post_id) ON DELETE CASCADE
    );
    """)
    print("✅ Table 'cluster_assignments' created")
    
    # Table 4: Clusters (metadata)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clusters (
        id SERIAL PRIMARY KEY,
        niche VARCHAR(50) NOT NULL,
        cluster_id INTEGER NOT NULL,
        cluster_version INTEGER DEFAULT 1,
        cluster_name VARCHAR(255),
        cluster_summary TEXT,
        keywords TEXT[],
        post_count INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(niche, cluster_id, cluster_version)
    );
    """)
    print("✅ Table 'clusters' created")
    
    # Create indexes for faster queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_niche ON posts(niche);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_embeddings_niche ON embeddings(niche);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cluster_assignments_niche ON cluster_assignments(niche);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cluster_assignments_version ON cluster_assignments(cluster_version);")
    print("✅ Indexes created")
    
    conn.commit()
    cursor.close()


def drop_all_tables(conn):
    """Drop all tables (use with caution!)"""
    cursor = conn.cursor()
    
    tables = ['cluster_assignments', 'clusters', 'embeddings', 'posts']
    for table in tables:
        cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
        print(f"✅ Table '{table}' dropped")
    
    conn.commit()
    cursor.close()


# ============================================
# DATA INSERTION FUNCTIONS
# ============================================

def insert_posts_from_df(conn, df):
    """
    Insert Reddit posts from DataFrame
    
    Parameters:
    -----------
    conn : psycopg2 connection
    df : pd.DataFrame with columns:
        post_id, niche, title, author, score, upvote_ratio, 
        num_comments, timestamp_utc, permalink, url, 
        selftext, full_text, text_translated
    """
    cursor = conn.cursor()
    
    # Prepare data
    data = []
    for _, row in df.iterrows():
        data.append((
            row['post_id'],
            row['niche'],
            row['title'],
            row.get('author'),
            row.get('score'),
            row.get('upvote_ratio'),
            row.get('num_comments'),
            row.get('timestamp_utc'),
            row.get('permalink'),
            row.get('url'),
            row.get('selftext'),
            row.get('full_text'),
            row.get('text_translated')
        ))
    
    # Batch insert
    execute_batch(cursor, """
        INSERT INTO posts (
            post_id, niche, title, author, score, upvote_ratio,
            num_comments, timestamp_utc, permalink, url,
            selftext, full_text, text_translated
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (post_id) DO NOTHING
    """, data)
    
    inserted = cursor.rowcount
    conn.commit()
    cursor.close()
    
    print(f"✅ Inserted {inserted} posts (duplicates skipped)")
    return inserted


def insert_embeddings(conn, post_ids, embeddings, niche):
    """
    Insert embeddings for posts
    
    Parameters:
    -----------
    conn : psycopg2 connection
    post_ids : list of post IDs
    embeddings : numpy array of shape (N, 384)
    niche : str, subreddit name
    """
    cursor = conn.cursor()
    
    data = []
    for post_id, embedding in zip(post_ids, embeddings):
        embedding_list = embedding.tolist()
        data.append((post_id, niche, embedding_list))
    
    # Batch insert
    execute_batch(cursor, """
        INSERT INTO embeddings (post_id, niche, embedding)
        VALUES (%s, %s, %s)
        ON CONFLICT (post_id) DO UPDATE SET
            embedding = EXCLUDED.embedding
    """, data)
    
    inserted = cursor.rowcount
    conn.commit()
    cursor.close()
    
    print(f"✅ Inserted {inserted} embeddings for '{niche}'")
    return inserted


def insert_cluster_assignments(conn, post_ids, cluster_labels, niche, version=1):
    """
    Insert cluster assignments
    
    Parameters:
    -----------
    post_ids : list of post IDs
    cluster_labels : list of cluster IDs
    niche : str
    version : int, cluster version number
    """
    cursor = conn.cursor()
    
    data = [(pid, niche, int(cid), version) 
            for pid, cid in zip(post_ids, cluster_labels)]
    
    execute_batch(cursor, """
        INSERT INTO cluster_assignments (post_id, niche, cluster_id, cluster_version)
        VALUES (%s, %s, %s, %s)
    """, data)
    
    inserted = cursor.rowcount
    conn.commit()
    cursor.close()
    
    print(f"✅ Inserted {inserted} cluster assignments for '{niche}' (v{version})")
    return inserted


def insert_cluster_metadata(conn, niche, cluster_id, version, name, summary, keywords, post_count):
    """Insert cluster metadata"""
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO clusters (niche, cluster_id, cluster_version, cluster_name, 
                            cluster_summary, keywords, post_count)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (niche, cluster_id, cluster_version) DO UPDATE SET
            cluster_name = EXCLUDED.cluster_name,
            cluster_summary = EXCLUDED.cluster_summary,
            keywords = EXCLUDED.keywords,
            post_count = EXCLUDED.post_count
    """, (niche, cluster_id, version, name, summary, keywords, post_count))
    
    conn.commit()
    cursor.close()


# ============================================
# QUERY FUNCTIONS
# ============================================

def get_posts_by_niche(conn, niche, limit=None):
    """Get all posts for a specific niche"""
    query = """
        SELECT * FROM posts 
        WHERE niche = %s
        ORDER BY timestamp_utc DESC
    """
    if limit:
        query += f" LIMIT {limit}"
    
    return pd.read_sql(query, conn, params=(niche,))


def get_embeddings_by_niche(conn, niche):
    """Get all embeddings for a specific niche"""
    query = """
        SELECT post_id, embedding FROM embeddings
        WHERE niche = %s
    """
    df = pd.read_sql(query, conn, params=(niche,))
    
    # Convert pgvector arrays back to numpy
    if len(df) > 0:
        embeddings = np.array([np.array(emb) for emb in df['embedding']])
        return df['post_id'].values, embeddings
    return None, None


def get_cluster_assignments(conn, niche, version=None):
    """Get cluster assignments for a niche"""
    if version:
        query = """
            SELECT * FROM cluster_assignments
            WHERE niche = %s AND cluster_version = %s
        """
        return pd.read_sql(query, conn, params=(niche, version))
    else:
        query = """
            SELECT * FROM cluster_assignments
            WHERE niche = %s
            ORDER BY cluster_version DESC
        """
        return pd.read_sql(query, conn, params=(niche,))


def get_posts_with_clusters(conn, niche, version=1):
    """Get posts joined with their cluster assignments"""
    query = """
        SELECT p.*, ca.cluster_id, c.cluster_name
        FROM posts p
        LEFT JOIN cluster_assignments ca ON p.post_id = ca.post_id
        LEFT JOIN clusters c ON ca.niche = c.niche 
            AND ca.cluster_id = c.cluster_id 
            AND ca.cluster_version = c.cluster_version
        WHERE p.niche = %s AND ca.cluster_version = %s
    """
    return pd.read_sql(query, conn, params=(niche, version))


def table_stats(conn):
    """Print statistics for all tables"""
    cursor = conn.cursor()
    
    print("\n" + "="*60)
    print("DATABASE STATISTICS")
    print("="*60)
    
    # Posts by niche
    cursor.execute("""
        SELECT niche, COUNT(*) as count 
        FROM posts 
        GROUP BY niche
        ORDER BY niche
    """)
    print("\n📊 Posts by Niche:")
    for row in cursor.fetchall():
        print(f"   {row[0]}: {row[1]:,} posts")
    
    # Total embeddings
    cursor.execute("SELECT COUNT(*) FROM embeddings")
    total_emb = cursor.fetchone()[0]
    print(f"\n🔢 Total Embeddings: {total_emb:,}")
    
    # Cluster assignments
    cursor.execute("""
        SELECT niche, cluster_version, COUNT(*) as count
        FROM cluster_assignments
        GROUP BY niche, cluster_version
        ORDER BY niche, cluster_version
    """)
    rows = cursor.fetchall()
    if rows:
        print(f"\n🎯 Cluster Assignments:")
        for row in rows:
            print(f"   {row[0]} (v{row[1]}): {row[2]:,} posts")
    
    # Clusters
    cursor.execute("""
        SELECT niche, cluster_version, COUNT(*) as count
        FROM clusters
        GROUP BY niche, cluster_version
        ORDER BY niche, cluster_version
    """)
    rows = cursor.fetchall()
    if rows:
        print(f"\n📦 Clusters:")
        for row in rows:
            print(f"   {row[0]} (v{row[1]}): {row[2]} clusters")
    
    print("="*60 + "\n")
    cursor.close()


# ============================================
# UTILITY FUNCTIONS
# ============================================

def reset_database(conn):
    """Drop and recreate all tables (DANGEROUS!)"""
    print("\n⚠️  WARNING: This will delete all data!")
    confirm = input("Type 'DELETE ALL' to confirm: ")
    
    if confirm == "DELETE ALL":
        drop_all_tables(conn)
        create_all_tables(conn)
        print("✅ Database reset complete")
    else:
        print("❌ Reset cancelled")