import psycopg2
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# PostgreSQL connection parameters
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "vector_store_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")

def get_connection():
    """Get a PostgreSQL database connection."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

# --- Query Functions ---
def query_get_vector_store_id(conn, workspace_id: str):
    cursor = conn.cursor()
    cursor.execute("SELECT vector_store_id FROM vector_store_map WHERE workspace_id = %s", (workspace_id,))
    result = cursor.fetchone()
    cursor.close()
    return result

def query_set_vector_store_id(conn, workspace_id: str, vector_store_id: str):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO vector_store_map (workspace_id, vector_store_id) 
        VALUES (%s, %s) 
        ON CONFLICT (workspace_id) 
        DO UPDATE SET vector_store_id = EXCLUDED.vector_store_id
    """, (workspace_id, vector_store_id))
    cursor.close()

# --- Public API ---
def init_db():
    """Initialize the database schema if it doesn't exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create the vector_store_map table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vector_store_map (
            workspace_id TEXT PRIMARY KEY,
            vector_store_id TEXT NOT NULL
        )
    """)
    
    conn.commit()
    cursor.close()
    conn.close()

def get_vector_store_id(workspace_id: str) -> Optional[str]:
    """Get vector store ID for a given workspace ID."""
    conn = get_connection()
    row = query_get_vector_store_id(conn, workspace_id)
    conn.close()
    return row[0] if row else None

def set_vector_store_id(workspace_id: str, vector_store_id: str):
    """Set vector store ID for a given workspace ID."""
    conn = get_connection()
    query_set_vector_store_id(conn, workspace_id, vector_store_id)
    conn.commit()
    conn.close() 