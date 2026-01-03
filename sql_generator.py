# End-to-end NL → SQL generation using Qwen2.5-32B with guardrails

import torch
from llm_loader import load_llm
from prompt_templates import SQL_SYSTEM_PROMPT, build_user_prompt
from sql_guardrails import validate_sql

import re


def _extract_sql_from_model_response(resp: str) -> str:
    """Extract a clean SQL statement from a model response.

    - Strips Markdown code fences (```sql ... ```), inline backticks, and extra text.
    - Returns the first SELECT statement found (case-insensitive), or the sanitized text if no SELECT found.
    """
    if not resp:
        return ""

    s = resp.strip()

    # Extract triple-backtick block if present
    m = re.search(r"```(?:sql)?\n([\s\S]*?)```", s, flags=re.IGNORECASE)
    if m:
        s = m.group(1).strip()

    # Remove any leftover backticks
    s = s.replace("`", "")

    # Try to find the first SELECT statement
    sel = re.search(r"\bSELECT\b", s, flags=re.IGNORECASE)
    if not sel:
        return s.strip()

    s = s[sel.start():]

    # Take up to the first semicolon (prefer single-statement responses)
    parts = s.split(";")
    stmt = parts[0].strip()

    return stmt

def generate_sql(user_query: str, schema_json: dict, tokenizer=None, model=None) -> str:
    """Generate SQL for a user query.

    If `tokenizer` and `model` are not provided, they will be lazily loaded via `load_llm()`.
    This avoids heavy model loading at import time which can cause crashes on machines without suitable GPU or PyTorch setup.
    """
    if tokenizer is None or model is None:
        try:
            tokenizer, model = load_llm()
        except RuntimeError as e:
            # If the failure is due to missing `accelerate` (required for device_map="auto"),
            # retry loading on CPU to provide a friendlier fallback.
            msg = str(e).lower()
            if "accelerate" in msg or "torch.set_default_device" in msg:
                tokenizer, model = load_llm(force_cpu=True)
            else:
                raise

    messages = [
        {"role": "system", "content": SQL_SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(user_query, schema_json)}
    ]

    input_text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    inputs = tokenizer(input_text, return_tensors="pt").to(model.device)

    import torch
    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=256,
            temperature=0.1,
            top_p=0.9
        )

    response = tokenizer.decode(
        output[0][inputs["input_ids"].shape[-1]:],
        skip_special_tokens=True
    ).strip()

    # Sanitize / extract SQL from the model response (strip code fences/backticks)
    cleaned = _extract_sql_from_model_response(response)

    # Preserve the INSUFFICIENT_INFORMATION sentinel if returned by the model
    if response == "INSUFFICIENT_INFORMATION" or cleaned == "INSUFFICIENT_INFORMATION":
        return "INSUFFICIENT_INFORMATION"

    # Validate and handle guardrail violations gracefully using the cleaned SQL.
    try:
        validate_sql(cleaned, schema_json)
        return cleaned
    except ValueError as e:
        # Attempt one retry with a stricter instruction to the model
        correction_msg = (
            "The previous SQL failed validation with the following error: "
            f"{e}.\nOnly return a single valid SELECT statement that uses tables and columns from the given schema, "
            "and avoid any forbidden keywords or non-SELECT operations. Return only the SQL query and nothing else.\n"
            f"Schema: {schema_json} \nPrevious attempt: {cleaned}"
        )

        messages = [
            {"role": "system", "content": SQL_SYSTEM_PROMPT},
            {"role": "user", "content": correction_msg}
        ]

        input_text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        inputs = tokenizer(input_text, return_tensors="pt").to(model.device)

        with torch.no_grad():
            output = model.generate(
                **inputs,
                max_new_tokens=256,
                temperature=0.1,
                top_p=0.9
            )

        candidate = tokenizer.decode(
            output[0][inputs["input_ids"].shape[-1]:],
            skip_special_tokens=True
        ).strip()

        candidate_clean = _extract_sql_from_model_response(candidate)

        try:
            validate_sql(candidate_clean, schema_json)
            return candidate_clean
        except ValueError as e2:
            # Return clear guardrail error instead of raising an exception so the demo doesn't crash
            return (
                f"GUARDRAIL_VIOLATION: {str(e2)} | Model attempts: "
                f"original={cleaned!r}, retry={candidate_clean!r}"
            )
