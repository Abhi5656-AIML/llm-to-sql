# CORRECT NL → Clarification → SQL → Execution → Explanation pipeline
# SQL generation is BLOCKED until clarification is resolved

import os
import json
from clarification_engine import check_clarification
from conversation_state import ConversationState
from sql_generator import generate_sql
from sql_executor import execute_sql
from result_explainer import explain_result

state = ConversationState()

AMBIGUOUS_KEYWORDS = {"top", "highest", "best", "most"}
DEFAULT_FILL = "by total revenue in the last 30 days"
# STRICT_MODE: when True, always require clarification for ambiguous keywords like 'top'
# and never allow implicit defaults. Default is read from the STRICT_MODE env var (1/true/yes = enabled).
STRICT_MODE = os.getenv("STRICT_MODE", "1").lower() in ("1", "true", "yes")

def set_strict_mode(value: bool):
    """Runtime setter to toggle strict mode for tests or runtime configuration."""
    global STRICT_MODE
    STRICT_MODE = bool(value)


def _has_unrequested_filters(sql: str, original_query: str, allowed_filter_cols=None) -> bool:
    """Return True if SQL includes WHERE filters that were not requested by the user.

    This protects against the model inventing additional filters (e.g., `WHERE city = 'New York'`).
    """
    import re
    if allowed_filter_cols is None:
        allowed_filter_cols = set()

    m = re.search(r"WHERE(.*?)(?:GROUP\s+BY|ORDER\s+BY|LIMIT|$)", sql, flags=re.IGNORECASE | re.S)
    if not m:
        return False
    where = m.group(1)

    # Remove string literals so they don't produce misleading tokens
    where_stripped = re.sub(r"'[^']*'", "''", where)

    # Find column tokens (qualified or bare)
    cols = re.findall(r"([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?)", where_stripped)

    # If any column is compared to a literal and that column is not allowed and not mentioned in original query -> unrequested
    for col in cols:
        bare = col.split('.')[-1]
        # If the original query mentions this column (e.g., 'city' or 'store'), it's probably requested
        if bare.lower() in original_query.lower():
            continue
        if bare in allowed_filter_cols:
            continue
        # Simple heuristic: if WHERE contains equality to a literal involving this column, mark it
        if re.search(rf"\b{re.escape(col)}\b\s*=\s*(?:['\"])", where, flags=re.IGNORECASE):
            return True
        # Numeric comparisons with literal numbers
        if re.search(rf"\b{re.escape(col)}\b\s*[<>]=?\s*\d+", where, flags=re.IGNORECASE):
            return True
    return False


def run_nl_to_sql(user_query: str, allow_defaults: bool = False):
    with open("schema.json") as f:
        schema = json.load(f)

    # Quick heuristic: if query contains ambiguous keywords and there's no pending clarification
    tokens = set(user_query.lower().split())
    if tokens.intersection(AMBIGUOUS_KEYWORDS) and not state.has_pending():
        # When strict mode is enabled, always require clarification for 'top' queries
        if STRICT_MODE:
            state.set_pending(user_query, question="Top by which metric (total revenue, number of orders, or return rate)?")
            return {
                "status": "needs_clarification",
                "question": "Top by which metric (total revenue, number of orders, or return rate)?"
            }

        # Non-strict behavior (legacy / optional): allow defaults if explicitly requested
        if allow_defaults:
            # Explicitly append system-defined defaults and forbid extra invented filters
            full_query = (
                f"{user_query} {DEFAULT_FILL} "
                "(apply defaults only; DO NOT add extra filters or invent values)"
            )
        else:
            state.set_pending(user_query, question="Top by which metric (total revenue, number of orders, or return rate)?")
            return {
                "status": "needs_clarification",
                "question": "Top by which metric (total revenue, number of orders, or return rate)?"
            }

    # -------------------------------
    # CASE 1: Pending clarification exists
    # -------------------------------
    if state.has_pending():
        # If the user repeated the SAME ambiguous query, re-ask the SAME clarification
        if state.is_same_pending(user_query):
            return {
                "status": "needs_clarification",
                "question": state.get_pending_question()
            }

        # If the user provided a clarification-like answer, merge and proceed WITHOUT re-validating clarification
        def _is_clarification_answer(q: str) -> bool:
            ql = q.strip().lower()
            metric_kw = {"revenue", "order", "orders", "return", "returns", "return rate", "total revenue", "number of orders"}
            time_kw = {"last", "month", "months", "year", "years", "day", "days", "week", "weeks", "since"}
            if ql.startswith(("by ", "for ", "in ", "last ", "the last ")):
                return True
            if any(k in ql for k in metric_kw):
                return True
            if any(k in ql for k in time_kw):
                return True
            # short answers like 'by total revenue' or 'last 6 months'
            if len(ql.split()) <= 6 and any(tok.isdigit() for tok in ql.split()):
                return True
            return False

        if _is_clarification_answer(user_query):
            full_query = state.resolve_pending(user_query)
        else:
            # Unrelated query — reset pending and treat as a fresh query
            state.reset_pending()
            # continue to normal clarification detection below
            pass
    elif 'full_query' not in locals():
        # Deterministic check for ambiguous 'top' queries when strict mode is enabled
        if STRICT_MODE and tokens.intersection(AMBIGUOUS_KEYWORDS):
            state.set_pending(user_query, question="Top by which metric (total revenue, number of orders, or return rate)?")
            return {
                "status": "needs_clarification",
                "question": "Top by which metric (total revenue, number of orders, or return rate)?"
            }

        # Check if clarification is required (fallback to model-based clarifier for other ambiguity types)
        clarification = check_clarification(user_query, schema)

        if clarification != "NO_CLARIFICATION_NEEDED":
            # If strict mode is enabled, never apply defaults automatically
            if not STRICT_MODE and allow_defaults:
                full_query = (
                    f"{user_query} {DEFAULT_FILL} "
                    "(apply defaults only; DO NOT add extra filters or invent values)"
                )
            else:
                state.set_pending(user_query, question=clarification)
                return {
                    "status": "needs_clarification",
                    "question": clarification
                }

        full_query = full_query if 'full_query' in locals() else user_query

    # -------------------------------
    # CASE 2: Safe to generate SQL
    # -------------------------------
    sql = generate_sql(full_query, schema)

    # If the model clearly couldn't produce a SQL, optionally retry with defaults (disabled in strict mode)
    if sql == "INSUFFICIENT_INFORMATION":
        if not STRICT_MODE and allow_defaults and DEFAULT_FILL not in full_query:
            full_query = f"{full_query} {DEFAULT_FILL}"
            sql = generate_sql(full_query, schema)
            if sql == "INSUFFICIENT_INFORMATION":
                return {
                    "status": "needs_clarification",
                    "question": "Please clarify the metric, grouping, or time range."
                }
        else:
            return {
                "status": "needs_clarification",
                "question": "Please clarify the metric, grouping, or time range."
            }

    # If the model violated guardrails, propagate an error
    if isinstance(sql, str) and sql.startswith("GUARDRAIL_VIOLATION:"):
        return {
            "status": "error",
            "sql": None,
            "error": sql
        }

    # Prevent the model from inventing extra filters when defaults are applied
    if allow_defaults and DEFAULT_FILL in full_query:
        allowed_filter_cols = {"order_date", "amount"}
        if _has_unrequested_filters(sql, user_query, allowed_filter_cols=allowed_filter_cols):
            return {
                "status": "needs_clarification",
                "question": "The model added filters not requested by you—please clarify filter criteria explicitly."
            }

    # -------------------------------
    # CASE 3: Execute SQL safely
    # -------------------------------
    # Ensure every query has a LIMIT clause to satisfy production constraints
    def _ensure_limit(stmt: str, default: int = 100) -> str:
        import re
        if not re.search(r"\bLIMIT\b", stmt, flags=re.IGNORECASE):
            return stmt.rstrip().rstrip(';') + f" LIMIT {default}"
        return stmt

    sql = _ensure_limit(sql, default=100)

    execution_result = execute_sql(sql)

    if "error" in execution_result:
        return {
            "status": "error",
            "sql": sql,
            "error": execution_result["error"]
        }

    # -------------------------------
    # CASE 4: Explain result
    # -------------------------------
    # Ensure the returned SQL includes a LIMIT before returning success
    sql = _ensure_limit(sql, default=100)

    explanation = explain_result(
        user_query=full_query,
        sql=sql,
        execution_result=execution_result
    )

    return {
        "status": "success",
        "sql": sql,
        "result": execution_result,
        "explanation": explanation
    }
