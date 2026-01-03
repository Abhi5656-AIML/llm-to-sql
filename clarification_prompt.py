# Prompt that STRICTLY decides whether clarification is required

CLARIFICATION_SYSTEM_PROMPT = """
You are an intent clarification engine for a data analytics system.

RULES:
- Determine if the query is ambiguous.
- Ambiguous means missing metric, grouping, filter, or time range.
- If ambiguous, ask ONE clarification question.
- If NOT ambiguous, respond EXACTLY with:
NO_CLARIFICATION_NEEDED

OUTPUT:
- One question OR exactly NO_CLARIFICATION_NEEDED
"""

def build_clarification_prompt(user_query: str, schema_json: dict) -> str:
    return f"""
DATABASE SCHEMA:
{schema_json}

USER QUERY:
{user_query}

Is clarification required?
"""
