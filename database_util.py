"""
database_util.py

Utility functions to manage the PostgreSQL database for trending topics:

- connect_postgres(): Connect to the default Postgres database
- create_database(): Create the project database if it doesn't exist
- conn = connect_database(): Connect to the project database
- drop_table(conn): Drop the trending_topics table if it exists
- create_table(conn): Create the trending_topics table
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

def drop_table(conn, table_name="trending_topics"):
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

def create_table(conn, table_name="trending_topics"):
    cursor = conn.cursor()
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id BIGINT PRIMARY KEY,
        text TEXT,
        text_en TEXT,
        created_at DATE,
        username TEXT,
        likes FLOAT,
        retweets FLOAT,
        topic TEXT,
        timestamp TIMESTAMP
    );
    """)
    cursor.close()
    conn.commit()
    print(f"New table '{table_name}' created")

def insert_csv(conn, csv_path="trending_topics.csv", table_name="trending_topics"):
    df = pd.read_csv(csv_path, dtype=str)
    df['id'] = df['id'].str.strip().str.replace('"','').astype('int')
    df['likes'] = df['likes'].replace(['', 'nan', None], pd.NA).astype('float')
    df['retweets'] = df['retweets'].replace(['', 'nan', None], pd.NA).astype('float')
    df['timestamp'] = df['timestamp'].replace(['', 'nan', None], pd.NA)
    
    cursor = conn.cursor()
    inserted_count = 0
    conflict_count = 0
    
    for _, row in df.iterrows():
        cursor.execute(
            f"""
            INSERT INTO {table_name} 
            (id, text, created_at, username, likes, retweets, topic, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                row['id'],
                row['text'],
                row['created_at'],
                row['username'],
                row['likes'] if pd.notna(row['likes']) else None,
                row['retweets'] if pd.notna(row['retweets']) else None,
                row['topic'],
                row['timestamp'] if pd.notna(row['timestamp']) else None
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

def table_stats(conn, table_name="trending_topics"):
    cursor = conn.cursor()
    
    cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
    total = cursor.fetchone()[0]

    print(f"{total} existing samples in '{table_name}'")

    cursor.close()