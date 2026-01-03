# Golden test cases for NL → SQL system
# These are deterministic and used for regression testing

TEST_CASES = [
    {
        "name": "Ambiguous top query",
        "input": "Show top stores",
        "expected_status": "needs_clarification"
    },
    {
        "name": "Clarification resolution",
        "conversation": [
            "Show top stores",
            "By total revenue in the last 6 months"
        ],
        "expected_status": "success"
    },
    {
        "name": "No implicit defaults",
        "input": "Show top stores",
        "expected_status": "needs_clarification"
    },
    {
        "name": "Valid aggregation query",
        "input": "Show total revenue per city",
        "expected_status": "success"
    },
    {
        "name": "Hallucinated column prevention",
        "input": "Show profit per store",
        "expected_status": "needs_clarification"
    }
]
