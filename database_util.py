"""
database_util.py

Utility functions to manage the PostgreSQL database for trending topics:

- connect_postgres(): Connect to the default Postgres database
- create_database(): Create the project database if it doesn't exist
- conn = connect_database(): Connect to the project database
- drop_table(conn): Drop the final_trendingtopics table if it exists
- create_table(conn): Create the final_trendingtopics table
- insert_csv(conn, csv_path="..."): Load and insert CSV data into the table
- table_stats(conn): Print the total number of samples in the table

"""

import pandas as pd
import psycopg2
from config import DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME

def connect_postgres():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

def create_database(dbname=DB_NAME):
    conn = connect_postgres()
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute(f"SELECT 1 FROM pg_database WHERE datname='{dbname}';")
    exists = cursor.fetchone()
    if not exists:
        cursor.execute(f"CREATE DATABASE {dbname};")
        print(f"New database '{dbname}' created")
    else:
        print(f"Database '{dbname}' already exists")
    cursor.close()
    conn.close()

def connect_database():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

def drop_table(conn, table_name="final_trendingtopics"):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = %s
        );
    """, (table_name,))
    if cursor.fetchone()[0]:
        cursor.execute(f"DROP TABLE {table_name};")
        print(f"Existing table '{table_name}' dropped")
    else:
        print(f"No existing table '{table_name}' to drop")
    cursor.close()

def create_table(conn, table_name="final_trendingtopics"):
    cursor = conn.cursor()
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        post_id TEXT PRIMARY KEY,
        niche TEXT,
        title TEXT,
        author TEXT,
        score FLOAT,
        upvote_ratio FLOAT,
        num_comments FLOAT,
        timestamp_utc TIMESTAMP,
        permalink TEXT,
        url TEXT,
        selftext TEXT,
        full_text TEXT,
        text_translated TEXT
    );
    """)
    cursor.close()
    conn.commit()
    print(f"New table '{table_name}' created")

def insert_csv(conn, csv_path="final_trendingtopics.csv", table_name="final_trendingtopics"):
    df = pd.read_csv(csv_path, dtype=str)
    df['score'] = df['score'].replace(['', 'nan', None], pd.NA).astype('float')
    df['upvote_ratio'] = df['upvote_ratio'].replace(['', 'nan', None], pd.NA).astype('float')
    df['num_comments'] = df['num_comments'].replace(['', 'nan', None], pd.NA).astype('float')
    df['timestamp_utc'] = df['timestamp_utc'].replace(['', 'nan', None], pd.NA)
    
    cursor = conn.cursor()
    inserted_count = 0
    conflict_count = 0
    
    for _, row in df.iterrows():
        cursor.execute(
            f"""
            INSERT INTO {table_name} 
            (post_id, niche, title, author, score, upvote_ratio, num_comments, timestamp_utc, permalink, url, selftext, full_text, text_translated)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (post_id) DO NOTHING
            """,
            (
                row['post_id'],
                row['niche'],
                row['title'],
                row['author'],
                row['score'] if pd.notna(row['score']) else None,
                row['upvote_ratio'] if pd.notna(row['upvote_ratio']) else None,
                row['num_comments'] if pd.notna(row['num_comments']) else None,
                row['timestamp_utc'] if pd.notna(row['timestamp_utc']) else None,
                row['permalink'],
                row['url'],
                row['selftext'],
                row['full_text'],
                row['text_translated']
            )
        )
        if cursor.rowcount == 1:
            inserted_count += 1
        else:
            conflict_count += 1
    
    conn.commit()
    cursor.close()
    print(f"{inserted_count} new samples added from '{csv_path}'")
    if conflict_count > 0:
        print(f"{conflict_count} skipped due to conflicts")

def table_stats(conn, table_name="final_trendingtopics"):
    cursor = conn.cursor()
    
    cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
    total = cursor.fetchone()[0]

    print(f"{total} existing samples in '{table_name}'")

    cursor.close()