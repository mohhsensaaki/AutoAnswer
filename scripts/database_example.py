"""
Database Connection Example for NewAfzzinaAI
============================================

This example demonstrates how to connect to the PostgreSQL database
using the environment variables created by the deployment script.

Database Configuration:
- Database Name: aidb
- Database User: admin
- Password: Set during deployment

Requirements:
- psycopg2 (already in requirements.txt)
- python-dotenv (already in requirements.txt)
"""

import os
import psycopg2
from dotenv import load_dotenv
import sys

# Load environment variables from .env file
load_dotenv()

def get_db_connection():
    """
    Create a connection to the PostgreSQL database using environment variables.
    
    Returns:
        psycopg2.connection: Database connection object
    """
    try:
        connection = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('DB_NAME', 'aidb'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        return connection
    except psycopg2.Error as e:
        print(f"Error connecting to database: {e}")
        return None

def test_database_connection():
    """
    Test the database connection and perform basic operations.
    """
    print("Testing database connection...")
    
    # Check if environment variables are loaded
    required_vars = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("Make sure to run the deployment script first to create the .env file")
        return False
    
    print("✅ All environment variables found")
    
    # Test connection
    conn = get_db_connection()
    if conn is None:
        print("❌ Failed to connect to database")
        return False
    
    print("✅ Database connection successful")
    
    try:
        # Create a cursor and execute a test query
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()
        print(f"✅ PostgreSQL version: {db_version[0]}")
        
        # Test creating a simple table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_table (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ Test table created successfully")
        
        # Insert test data
        cursor.execute("""
            INSERT INTO test_table (name) VALUES (%s) 
            ON CONFLICT DO NOTHING
        """, ("Test Connection",))
        
        # Query test data
        cursor.execute("SELECT * FROM test_table LIMIT 5")
        results = cursor.fetchall()
        print(f"✅ Test query successful, found {len(results)} records")
        
        # Commit the transaction
        conn.commit()
        print("✅ All database operations completed successfully")
        
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Database operation failed: {e}")
        conn.rollback()
        return False
        
    finally:
        cursor.close()
        conn.close()
        print("✅ Database connection closed")

def create_sample_schema():
    """
    Create sample tables that might be useful for an AI application.
    """
    print("\nCreating sample AI database schema...")
    
    conn = get_db_connection()
    if conn is None:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                title VARCHAR(200),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
                role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Documents table (for vector store)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                filename VARCHAR(255) NOT NULL,
                content TEXT,
                file_size INTEGER,
                file_type VARCHAR(50),
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for better performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conversation_id 
            ON messages(conversation_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_user_id 
            ON documents(user_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_user_id 
            ON conversations(user_id)
        """)
        
        conn.commit()
        print("✅ Sample AI database schema created successfully")
        
        # Display table information
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        tables = cursor.fetchall()
        print(f"✅ Created {len(tables)} tables: {', '.join([t[0] for t in tables])}")
        
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Failed to create schema: {e}")
        conn.rollback()
        return False
        
    finally:
        cursor.close()
        conn.close()

def main():
    """
    Main function to test database connection and create sample schema.
    """
    print("NewAfzzinaAI Database Connection Test")
    print("=" * 40)
    
    # Test basic connection
    if not test_database_connection():
        print("\n❌ Database connection test failed")
        sys.exit(1)
    
    # Ask user if they want to create sample schema
    print("\nWould you like to create sample AI database schema? (y/N): ", end="")
    create_schema = input().lower().strip()
    
    if create_schema in ['y', 'yes']:
        if create_sample_schema():
            print("\n✅ Database setup completed successfully!")
        else:
            print("\n❌ Schema creation failed")
            sys.exit(1)
    else:
        print("\n✅ Database connection test completed successfully!")
    
    print("\nYou can now use the database in your FastAPI application!")
    print("Connection details are stored in the .env file.")

if __name__ == "__main__":
    main() 