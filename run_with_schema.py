"""Run NL->SQL generation using a local model and a schema JSON file (no DB required).

Usage examples:

# Use a mock model (no heavy deps)
python run_with_schema.py --mode mock --query "List top 5 customers by revenue" --schema-file schema.json

# Use a local HTTP server exposing OpenAI-compatible chat completions
python run_with_schema.py --mode http --api-base http://localhost:8000/v1 --query "..." --schema-file schema.json

# Use local Transformers model (will load the model via `load_llm()`)
python run_with_schema.py --mode transformers --model-name Qwen/Qwen2.5-32B-Instruct --query "..." --schema-file schema.json
"""
import argparse
import json
import sys
from prompt_templates import SQL_SYSTEM_PROMPT, build_user_prompt
from sql_guardrails import validate_sql


def load_schema(path: str):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        raise RuntimeError(f"Failed to load schema from {path}: {e}") from e


def run_mock(query: str, schema: dict):
    # Return a simple placeholder SQL for development without a model
    # Try to create a basic SELECT using first table/column
    tables = list(schema.keys())
    if not tables:
        raise RuntimeError("Schema is empty; cannot create mock SQL")
    t = tables[0]
    cols = list(schema[t].get("columns", {}).keys())
    col = cols[0] if cols else "*"
    sql = f"SELECT {col} FROM {t} LIMIT 5"
    return sql


def run_http(query: str, schema: dict, api_base: str, model_name: str):
    try:
        from qwen_local import LocalQwenClient
    except Exception:
        raise RuntimeError("Local HTTP client not available. Ensure `qwen_local.py` is present.")

    client = LocalQwenClient(api_base=api_base, model=model_name)
    messages = [
        {"role": "system", "content": SQL_SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(query, schema)}
    ]

    resp = client.chat(messages)
    return resp


def run_transformers(query: str, schema: dict, model_name: str):
    try:
        from llm_loader import load_llm
        from sql_generator import generate_sql
    except Exception as e:
        raise RuntimeError("transformers/PyTorch are required for `transformers` mode. Install them first.") from e

    tokenizer, model = load_llm(model_name)
    return generate_sql(query, schema, tokenizer=tokenizer, model=model)


def main():
    parser = argparse.ArgumentParser(description="Run NL->SQL generation with a local model and schema file")
    parser.add_argument("--schema-file", default="schema.json", help="Path to schema JSON file")
    parser.add_argument("--query", required=True, help="Natural language question to convert to SQL")
    parser.add_argument("--mode", choices=["mock", "http", "transformers"], default="mock",
                        help="Which backend to use: mock (no model), http (LocalQwenClient), transformers (local HF model)")
    parser.add_argument("--api-base", default=None, help="Base URL for local HTTP server (http mode)")
    parser.add_argument("--model-name", default="qwen-2.5-32b", help="Model name (http mode) or repo id (transformers mode)")
    parser.add_argument("--no-validate", action="store_true", help="Skip SQL guardrail validation")
    parser.add_argument("--save-to", default=None, help="Save generated SQL to file")
    args = parser.parse_args()

    try:
        schema = load_schema(args.schema_file)
    except Exception as e:
        print("Error loading schema:", e, file=sys.stderr)
        sys.exit(2)

    try:
        if args.mode == "mock":
            sql = run_mock(args.query, schema)
        elif args.mode == "http":
            api_base = args.api_base or "http://localhost:8000/v1"
            sql = run_http(args.query, schema, api_base, args.model_name)
        else:
            # transformers
            sql = run_transformers(args.query, schema, args.model_name)

        sql = sql.strip()

        if not args.no_validate:
            try:
                validate_sql(sql, schema)
            except Exception as e:
                print("Generated SQL failed validation:", e, file=sys.stderr)
                sys.exit(3)

        print("\nGenerated SQL:\n")
        print(sql)

        if args.save_to:
            with open(args.save_to, "w") as f:
                f.write(sql)
            print(f"\nSaved SQL to {args.save_to}")

    except KeyboardInterrupt:
        print("Interrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print("Generation failed:", e, file=sys.stderr)
        sys.exit(4)


if __name__ == "__main__":
    main()
