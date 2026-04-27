"""
setup_database.py - One-time database setup script

Run this ONCE to set up your database structure
"""

from database_util import (
    create_database, 
    connect_database, 
    enable_pgvector,
    create_all_tables,
    table_stats
)

def main():
    print("\n" + "="*60)
    print("REDDIT TREND FINDER - DATABASE SETUP")
    print("="*60 + "\n")
    
    # Step 1: Create database
    print("Step 1: Creating database...")
    create_database()
    
    # Step 2: Connect to database
    print("\nStep 2: Connecting to database...")
    conn = connect_database()
    print("✅ Connected to database")
    
    # Step 3: Enable pgvector
    print("\nStep 3: Enabling pgvector extension...")
    enable_pgvector(conn)
    
    # Step 4: Create tables
    print("\nStep 4: Creating tables...")
    create_all_tables(conn)
    
    # Step 5: Show stats
    print("\nStep 5: Database ready!")
    table_stats(conn)
    
    conn.close()
    print("✅ Setup complete!\n")

if __name__ == "__main__":
    main()