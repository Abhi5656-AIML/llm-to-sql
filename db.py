# db.py
"""
Database connection helper.
Provides a clear error if the MySQL driver is not installed.
"""
try:
    import mysql.connector as mysql_connector
except Exception:
    mysql_connector = None


def get_connection():
    if mysql_connector is None:
        raise RuntimeError(
            "MySQL driver is not installed. Install it with: pip install mysql-connector-python"
        )

    return mysql_connector.connect(
        host="localhost",
        user="nlsql_user",
        password="password",
        database="nlsql_db"
    )
