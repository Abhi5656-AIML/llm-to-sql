# Uses Qwen2.5-32B to decide if clarification is needed

import torch
from llm_loader import load_llm
from clarification_prompt import (
    CLARIFICATION_SYSTEM_PROMPT,
    build_clarification_prompt
)

tokenizer, model = load_llm()

def check_clarification(user_query: str, schema_json: dict) -> str:
    messages = [
        {"role": "system", "content": CLARIFICATION_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": build_clarification_prompt(user_query, schema_json)
        }
    ]

    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    inputs = tokenizer(text, return_tensors="pt").to(model.device)

    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=64,
            temperature=0.2
        )

    response = tokenizer.decode(
        output[0][inputs["input_ids"].shape[-1]:],
        skip_special_tokens=True
    ).strip()

    # Normalize common "no clarification needed" replies coming from the model.
    import re
    sanitized = response

    # Remove code fences and backticks that some models include
    sanitized = re.sub(r"```(?:[\s\S]*?)```", "", sanitized, flags=re.IGNORECASE).strip()
    sanitized = sanitized.replace("`", "").strip()

    lowered = sanitized.lower().strip().rstrip('.!?')
    if lowered in ("no clarification needed", "no", "none", "no clarification", "no_clarification_needed") or lowered.startswith("no "):
        return "NO_CLARIFICATION_NEEDED"

    return sanitized
