import psycopg2
from config import DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME

try:
    # Connect to database
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    
    print("✅ Connected to PostgreSQL!")
    
    # Test pgvector
    cursor = conn.cursor()
    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    cursor.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector';")
    version = cursor.fetchone()
    
    if version:
        print(f"✅ pgvector installed! Version: {version[0]}")
    else:
        print("⚠️  pgvector not found")
    
    # Test database info
    cursor.execute("SELECT version();")
    db_version = cursor.fetchone()[0]
    print(f"✅ PostgreSQL version: {db_version.split(',')[0]}")
    
    cursor.close()
    conn.close()
    print("\n🎉 Everything is working!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nTroubleshooting:")
    print("1. Is Docker running? Check Docker Desktop")
    print("2. Is container running? Run: docker-compose ps")
    print("3. Check config.py matches docker-compose.yml")