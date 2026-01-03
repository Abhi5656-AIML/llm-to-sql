# FastAPI backend for NL → SQL system

from fastapi import FastAPI
from pydantic import BaseModel
from nl_to_sql_pipeline import run_nl_to_sql

app = FastAPI(title="NL → SQL Analytics API")

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    status: str
    sql: str | None = None
    result: dict | None = None
    explanation: str | None = None
    question: str | None = None
    error: str | None = None

@app.post("/query", response_model=QueryResponse)
def query_db(req: QueryRequest):
    response = run_nl_to_sql(req.query)
    return response
