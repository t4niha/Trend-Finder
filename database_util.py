import pandas as pd
import psycopg2

# Connect to PostgreSQL
conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password="taniha",
    host="localhost",
    port="5432"
)
conn.autocommit = True
cursor = conn.cursor()

# Create database if it doesn't exist
cursor.execute("SELECT 1 FROM pg_database WHERE datname='trend_finder';")
exists = cursor.fetchone()
if not exists:
    cursor.execute("CREATE DATABASE trend_finder;")
    print("New database 'trend_finder' created.")
else:
    print("Database 'trend_finder' already exists.")
cursor.close()
conn.close()

# Connect to the database
conn = psycopg2.connect(
    dbname="trend_finder",
    user="postgres",
    password="taniha",
    host="localhost",
    port="5432"
)
cursor = conn.cursor()

# Drop table if it exists
cursor.execute("""
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_name = 'trending_topics'
);
""")
table_exists = cursor.fetchone()[0]

if table_exists:
    cursor.execute("DROP TABLE trending_topics;")
    print("Old table 'trending_topics' dropped, new table created.")
else:
    print("New table 'trending_topics' created.")

# Create new table
cursor.execute("""
CREATE TABLE trending_topics (
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

# Load and clean CSV
df = pd.read_csv("trending_topics.csv", dtype=str)

df['id'] = df['id'].str.strip().str.replace('"','').astype('int')

df['likes'] = df['likes'].replace(['', 'nan', None], pd.NA).astype('float')
df['retweets'] = df['retweets'].replace(['', 'nan', None], pd.NA).astype('float')
df['timestamp'] = df['timestamp'].replace(['', 'nan', None], pd.NA)

# Insert rows into PostgreSQL
for _, row in df.iterrows():
    cursor.execute(
        """
        INSERT INTO trending_topics 
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

conn.commit()
cursor.close()
conn.close()

print("CSV imported successfully.")