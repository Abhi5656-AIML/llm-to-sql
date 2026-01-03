# Secure SQL execution layer for MySQL
# Executes ONLY validated SELECT queries
# Includes timeout, row limits, and safe result formatting

import mysql.connector
from mysql.connector import Error
from db import get_connection

MAX_ROWS = 1000          # Hard limit on rows returned
QUERY_TIMEOUT = 5        # Seconds

def execute_sql(sql: str):
    """
    Executes a validated SELECT SQL query safely.
    Returns results as list of dictionaries.
    """

    if not sql.strip().upper().startswith("SELECT"):
        # Return an error dict instead of raising to make the executor safe to call
        # from higher-level code that may not catch exceptions.
        return {
            "error": "Only SELECT queries are allowed for execution"
        }

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Enforce execution timeout (MySQL supports MAX_EXECUTION_TIME hint)
        timed_sql = f"SELECT /*+ MAX_EXECUTION_TIME({QUERY_TIMEOUT * 1000}) */ * FROM ({sql}) AS safe_query LIMIT {MAX_ROWS}"

        cursor.execute(timed_sql)
        results = cursor.fetchall()

        return {
            "row_count": len(results),
            "data": results
        }

    except Error as e:
        return {
            "error": str(e)
        }

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
