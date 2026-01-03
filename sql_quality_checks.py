# Additional SQL quality validation for executed queries

def check_sql_quality(sql: str):
    """
    Ensures SQL follows required production constraints.
    """
    sql_upper = sql.upper()

    if "SELECT" not in sql_upper:
        return False, "Not a SELECT query"

    if "LIMIT" not in sql_upper:
        return False, "Missing LIMIT clause"

    if "ORDER BY" not in sql_upper and "TOP" in sql_upper:
        return False, "Top query without ORDER BY"

    return True, "SQL quality OK"
