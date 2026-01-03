# SQL safety + hallucination prevention layer
# This is mandatory for production use

# Try to import sqlparse for robust parsing; if not available, fall back to
# a lightweight heuristic parser so the module still works in minimal envs.
try:
    import sqlparse
    _HAS_SQLPARSE = True
except Exception:
    sqlparse = None
    _HAS_SQLPARSE = False

FORBIDDEN_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP",
    "ALTER", "CREATE", "TRUNCATE", "REPLACE"
}

def validate_sql(sql: str, schema: dict):
    """Validate SQL for safety and hallucinations.

    Falls back to simple heuristics if `sqlparse` is not installed.
    """

    if _HAS_SQLPARSE:
        parsed = sqlparse.parse(sql)
        if not parsed:
            raise ValueError("Invalid SQL")

        statement = parsed[0]

        # 1. Enforce SELECT-only
        if statement.get_type() != "SELECT":
            raise ValueError("Only SELECT queries are allowed")

        # Collect tokens (identifiers) for hallucination checking
        tokens = [t.value for t in statement.flatten() if t.ttype is None]

        upper_sql = sql.upper()

    else:
        # Lightweight fallback parsing
        upper_sql = sql.strip().upper()
        if not upper_sql.startswith("SELECT"):
            raise ValueError("Only SELECT queries are allowed (and sqlparse is not available)")

        # crude token extraction: find dotted identifiers like table.column
        import re
        tokens = re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)", sql)
        # Normalize tokens to 'table.column' format for downstream checks
        tokens = [f"{t}.{c}" for t, c in tokens]

    # 2. Block forbidden keywords
    for keyword in FORBIDDEN_KEYWORDS:
        if keyword in upper_sql:
            raise ValueError(f"Forbidden SQL keyword detected: {keyword}")

    # 3. Check table & column hallucination
    allowed_tables = set(schema.keys())

    # Build a set of all allowed column names across the schema for bare-column checks
    allowed_columns = set()
    for t, info in schema.items():
        cols = info.get("columns", {})
        for c in cols.keys():
            allowed_columns.add(c)

    # schema expected shape: {table: {"columns": {col: type, ...}, ...}, ...}
    for token in tokens:
        if "." in token:
            table, col = token.split(".", 1)
            if table not in allowed_tables:
                raise ValueError(f"Hallucinated table: {table}")
            if col not in schema[table]["columns"]:
                raise ValueError(f"Hallucinated column: {table}.{col}")

    # Additional checks for bare columns used in clauses like SELECT, WHERE, GROUP BY, ORDER BY
    # These can cause runtime MySQL errors if the model invents a column name without qualifying it.
    import re
    import difflib

    def _suggest(col: str) -> str:
        match = difflib.get_close_matches(col, list(allowed_columns), n=1)
        return f" Did you mean: {match[0]}?" if match else ""

    clauses = {}
    # SELECT clause
    m = re.search(r"SELECT(.*?)FROM", sql, flags=re.IGNORECASE | re.S)
    if m:
        clauses['select'] = m.group(1)
    # WHERE clause
    m = re.search(r"WHERE(.*?)(?:GROUP\s+BY|ORDER\s+BY|LIMIT|$)", sql, flags=re.IGNORECASE | re.S)
    if m:
        clauses['where'] = m.group(1)
    # GROUP BY
    m = re.search(r"GROUP\s+BY(.*?)(?:ORDER\s+BY|LIMIT|$)", sql, flags=re.IGNORECASE | re.S)
    if m:
        clauses['group'] = m.group(1)
    # ORDER BY
    m = re.search(r"ORDER\s+BY(.*?)(?:LIMIT|$)", sql, flags=re.IGNORECASE | re.S)
    if m:
        clauses['order'] = m.group(1)

    sql_keywords = {"ASC", "DESC", "AND", "OR", "BY", "AS", "ON", "IN", "NOT", "NULL", "IS", "LIKE", "BETWEEN"}
    # Extended list of SQL/MySQL built-in functions to avoid misclassification as columns
    sql_functions = {
        "SUM", "COUNT", "MAX", "MIN", "AVG",
        "DATE", "DATE_SUB", "DATE_ADD", "DATEDIFF", "DATE_FORMAT",
        "STRFTIME", "CURDATE", "NOW", "MONTH", "YEAR", "DAY",
        "EXTRACT", "TIMESTAMPDIFF", "COALESCE", "IFNULL", "CAST",
        "CONCAT", "SUBSTRING", "ROUND", "LOWER", "UPPER", "INTERVAL"
    }

    # Extract alias names from SELECT clause to avoid flagging them as hallucinations
    alias_names = set()
    if 'select' in clauses:
        sel = clauses['select']
        alias_names.update(re.findall(r"\bAS\s+([A-Za-z_][A-Za-z0-9_]*)", sel, flags=re.IGNORECASE))
        # aliases without AS, e.g., "SUM(x) total_revenue"
        alias_names.update(re.findall(r"\)\s*([A-Za-z_][A-Za-z0-9_]*)", sel))


    # Identify tables and aliases present in FROM and JOIN clauses
    referenced_tables = []  # list of (table_name, alias_or_name)
    # FROM main tables (handle comma-separated lists)
    m = re.search(r"FROM\s+([^\n]*)", sql, flags=re.IGNORECASE)
    if m:
        from_part = m.group(1)
        # split on commas for simple multiple-table FROM lists
        for piece in from_part.split(','):
            piece = piece.strip()
            if not piece:
                continue
            # match `table [AS] alias` or just `table alias`
            mm = re.match(r"([A-Za-z_][A-Za-z0-9_]*)(?:\s+(?:AS\s+)?([A-Za-z_][A-Za-z0-9_]*))?", piece, flags=re.IGNORECASE)
            if mm:
                tbl = mm.group(1)
                alias = mm.group(2) or tbl
                referenced_tables.append((tbl, alias))

    # JOIN clauses
    for mm in re.finditer(r"JOIN\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s+(?:AS\s+)?([A-Za-z_][A-Za-z0-9_]*))?", sql, flags=re.IGNORECASE):
        tbl = mm.group(1)
        alias = mm.group(2) or tbl
        referenced_tables.append((tbl, alias))

    # Convert to sets for quick lookups
    referenced_table_names = set(t for t, _ in referenced_tables)
    referenced_aliases = set(a for _, a in referenced_tables)

    identifiers = set()
    for name, text in clauses.items():
        # Remove string literals
        text = re.sub(r"'[^']*'", "", text)
        # Find bare identifiers and dotted identifiers
        for tok in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?)\b", text):
            up = tok.upper()
            # Skip SQL keywords
            if up in sql_keywords:
                continue
            # Skip token if it appears to be a function call like NAME(...)
            if re.search(rf"\b{re.escape(tok)}\s*\(", text):
                continue
            # Skip known SQL functions (uppercase comparison)
            if up in sql_functions:
                continue
            # Skip known table names
            if tok in allowed_tables or tok.split('.')[0] in allowed_tables:
                continue
            # Skip aliases from SELECT
            if tok in alias_names or tok in referenced_aliases:
                continue
            identifiers.add(tok)

    # Check each identifier that looks like a bare column or qualified identifier
    for ident in identifiers:
        if "." in ident:
            # qualified like table.col or alias.col
            table_part, col_part = ident.split('.', 1)
            # If alias used, resolve to table name if possible
            table_name = table_part
            for t, a in referenced_tables:
                if a == table_part:
                    table_name = t
                    break
            if table_name not in schema:
                raise ValueError(f"Referenced table not found in schema: {table_part}")
            if col_part not in schema[table_name]['columns']:
                suggestion = _suggest(col_part)
                raise ValueError(f"Hallucinated column: {table_part}.{col_part}.{suggestion}")
        else:
            # bare column: ensure it exists in at least one referenced table
            col = ident
            if col not in allowed_columns:
                suggestion = _suggest(col)
                raise ValueError(f"Hallucinated column: {col}.{suggestion}")

            # If there are referenced tables, check that at least one of them contains the column
            if referenced_table_names:
                found = False
                candidate_tables = []
                for t in referenced_table_names:
                    if col in schema[t]['columns']:
                        found = True
                        candidate_tables.append(t)
                if not found:
                    # Column exists in schema but not in any referenced table — likely missing join
                    # Suggest the most likely table
                    match = difflib.get_close_matches(col, list(allowed_columns), n=1)
                    suggested_table = None
                    for tbl, info in schema.items():
                        if col in info.get('columns', {}):
                            suggested_table = tbl
                            break
                    suggestion = f" Column '{col}' exists in table '{suggested_table}'. Did you mean to JOIN that table?" if suggested_table else _suggest(col)
                    raise ValueError(f"Hallucinated column: {col}.{suggestion}")

    return True
