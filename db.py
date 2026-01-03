# db.py
import os
import mysql.connector
from mysql.connector import pooling

# ---- Load from environment variables ----
DB_CONFIG = {
    "host": os.environ.get("DB_HOST"),
    "user": os.environ.get("DB_USER"),
    "password": os.environ.get("DB_PASSWORD"),
    "database": os.environ.get("DB_NAME"),
    "port": int(os.environ.get("DB_PORT", 3306)),
    "ssl_disabled": False,
    "connection_timeout": 10,
}

# ---- Connection Pool (IMPORTANT) ----
connection_pool = pooling.MySQLConnectionPool(
    pool_name="nlsql_pool",
    pool_size=5,
    **DB_CONFIG
)

def get_connection():
    try:
        return connection_pool.get_connection()
    except Exception as e:
        raise RuntimeError(f"Database connection failed: {e}")
