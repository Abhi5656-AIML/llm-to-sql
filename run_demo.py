# Demo runner for NL → SQL using Qwen2.5-32B

import json
from sql_generator import generate_sql

with open("schema.json") as f:
    schema = json.load(f)

query = "Show total revenue per city for the last 6 months where return rate is above 10%"

sql = generate_sql(query, schema)
print("\nGenerated SQL:\n")
print(sql)
