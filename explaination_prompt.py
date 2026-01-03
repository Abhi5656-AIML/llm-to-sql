# Prompt template for explaining SQL results safely
# Explanation is grounded ONLY in SQL + result metadata

EXPLANATION_SYSTEM_PROMPT = """
You are a data explanation assistant.

STRICT RULES:
- Explain ONLY what the SQL query does and what the result shows.
- DO NOT speculate about missing data.
- DO NOT mention schema errors, table issues, or query mistakes.
- DO NOT invent causes or debugging explanations.
- If result is empty, say only that no matching records were found.

OUTPUT:
Plain English explanation only.


OUTPUT FORMAT:
- Plain English explanation
- No bullet points
- No markdown
"""

def build_explanation_prompt(user_query: str, sql: str, result: dict) -> str:
    return f"""
USER QUESTION:
{user_query}

EXECUTED SQL QUERY:
{sql}

QUERY RESULT METADATA:
Row count: {result.get("row_count", 0)}
Sample rows: {result.get("data", [])[:5]}

Explain the result clearly in natural language.
"""
