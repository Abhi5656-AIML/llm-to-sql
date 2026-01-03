# sql_generator.py

from prompt_templates import SQL_SYSTEM_PROMPT, build_user_prompt


def generate_sql(llm, user_query, schema_json):
    messages = [
        {"role": "system", "content": SQL_SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(user_query, schema_json)}
    ]

    response = llm.chat(messages)

    sql = response.strip()

    if not sql.upper().startswith("SELECT"):
        raise ValueError("Unsafe or invalid SQL generated")

    return sql


