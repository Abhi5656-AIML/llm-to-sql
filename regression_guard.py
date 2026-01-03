# Prevents silent regressions in future changes

from sql_quality_checks import check_sql_quality

def regression_check(response: dict):
    if response["status"] != "success":
        return True

    sql = response.get("sql")
    valid, reason = check_sql_quality(sql)

    if not valid:
        # Include the offending SQL (truncated) in the error to aid debugging
        snippet = (sql[:200] + '...') if isinstance(sql, str) and len(sql) > 200 else sql
        raise RuntimeError(f"Regression detected: {reason}. Offending SQL: {snippet!r}")

    return True
