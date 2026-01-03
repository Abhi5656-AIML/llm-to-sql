import mysql.connector
import json
from db import get_connection


def _get(row, key, pos=0):
    """Safely extract a column from a DB row.

    Supports dictionary rows with different key casings (e.g. TABLE_NAME) and
    tuple/list rows (by position). If the row contains a single value, that
    value is returned regardless of key.
    """
    if isinstance(row, dict):
        # direct match
        if key in row:
            return row[key]
        # case-insensitive match
        k_lower = key.lower()
        for k, v in row.items():
            if k.lower() == k_lower:
                return v
        # fallback: single-column row
        if len(row) == 1:
            return list(row.values())[0]
        raise KeyError(f"Column '{key}' not found in DB row. Available columns: {list(row.keys())}")
    else:
        # assume sequence-like
        try:
            return row[pos]
        except Exception:
            raise KeyError(f"Cannot extract '{key}' from row of type {type(row)}: {row}")


def extract_schema(database_name="nlsql_db"):
    try:
        conn = get_connection()
    except Exception as e:
        raise RuntimeError(
            "Failed to connect to MySQL. Ensure the server is running and credentials in `db.py` are correct. "
            f"Driver error: {e}"
        ) from e

    cursor = conn.cursor(dictionary=True)

    schema = {}

    # -------------------------------
    # 1. Get all tables
    # -------------------------------
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = %s
    """, (database_name,))
    
    tables = [_get(row, "table_name") for row in cursor.fetchall()]

    for table in tables:
        schema[table] = {
            "columns": {},
            "primary_key": [],
            "foreign_keys": []
        }

        # -------------------------------
        # 2. Get columns + data types
        # -------------------------------
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
        """, (database_name, table))

        for row in cursor.fetchall():
            col_name = _get(row, "column_name")
            data_type = _get(row, "data_type")
            schema[table]["columns"][col_name] = str(data_type).upper()

        # -------------------------------
        # 3. Get primary keys
        # -------------------------------
        cursor.execute("""
            SELECT column_name
            FROM information_schema.key_column_usage
            WHERE table_schema = %s
              AND table_name = %s
              AND constraint_name = 'PRIMARY'
        """, (database_name, table))

        schema[table]["primary_key"] = [
            _get(row, "column_name") for row in cursor.fetchall()
        ]

        # -------------------------------
        # 4. Get foreign keys
        # -------------------------------
        cursor.execute("""
            SELECT
                column_name,
                referenced_table_name,
                referenced_column_name
            FROM information_schema.key_column_usage
            WHERE table_schema = %s
              AND table_name = %s
              AND referenced_table_name IS NOT NULL
        """, (database_name, table))

        for row in cursor.fetchall():
            col = _get(row, "column_name")
            ref_table = _get(row, "referenced_table_name")
            ref_col = _get(row, "referenced_column_name")
            fk = f"{col} → {ref_table}.{ref_col}"
            schema[table]["foreign_keys"].append(fk)

    cursor.close()
    conn.close()
    return schema


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract DB schema or run a dry-run test")
    parser.add_argument("--dry-run", action="store_true", help="Run local tests for _get without connecting to a DB")
    parser.add_argument("--database", default="nlsql_db", help="Database name to extract from")
    args = parser.parse_args()

    if args.dry_run:
        print("Running dry-run tests for _get()...")
        # dict with lowercase keys
        r1 = {"table_name": "users"}
        assert _get(r1, "table_name") == "users"
        # dict with uppercase keys
        r2 = {"TABLE_NAME": "orders"}
        assert _get(r2, "table_name") == "orders"
        # single-column dict
        r3 = {"some_col": "value"}
        assert _get(r3, "missing_col") == "value"
        # tuple row
        r4 = ("products",)
        assert _get(r4, "table_name", pos=0) == "products"
        print("✅ _get tests passed")
        raise SystemExit(0)

    schema_json = extract_schema(args.database)
    
    with open("schema.json", "w") as f:
        json.dump(schema_json, f, indent=2)

    print("✅ Schema extracted and saved to schema.json")
