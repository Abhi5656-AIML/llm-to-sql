# Natural language explanation generator using Qwen2.5-32B
# This does NOT touch the database

import torch
from llm_loader import load_llm
from explaination_prompt import (
    EXPLANATION_SYSTEM_PROMPT,
    build_explanation_prompt
)

tokenizer, model = load_llm()

def explain_result(user_query: str, sql: str, execution_result: dict) -> str:
    """
    Generates a grounded natural-language explanation
    for the executed SQL and its result.
    """

    messages = [
        {"role": "system", "content": EXPLANATION_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": build_explanation_prompt(
                user_query=user_query,
                sql=sql,
                result=execution_result
            )
        }
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
            max_new_tokens=200,
            temperature=0.2,
            top_p=0.9
        )

    explanation = tokenizer.decode(
        output[0][inputs["input_ids"].shape[-1]:],
        skip_special_tokens=True
    ).strip()

    return explanation
