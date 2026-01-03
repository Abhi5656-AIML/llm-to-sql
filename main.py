# main.py
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from nl_to_sql_pipeline import run_nl_to_sql
import os

app = FastAPI(title="NL → SQL Analytics")

# ---------- API MODEL ----------
class QueryRequest(BaseModel):
    query: str

# ---------- API ENDPOINT ----------
@app.post("/query")
def query_db(req: QueryRequest):
    return run_nl_to_sql(req.query)

# ---------- UI ENDPOINT ----------
@app.get("/", response_class=HTMLResponse)
def home():
    html_path = os.path.join("templates", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()
