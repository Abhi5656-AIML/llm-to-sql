# Automated evaluation runner for NL → SQL system

from test_cases import TEST_CASES
from evaluation_metrics import EvaluationMetrics
from nl_to_sql_pipeline import run_nl_to_sql

def run_tests():
    metrics = EvaluationMetrics()

    for test in TEST_CASES:
        print(f"\nRunning test: {test['name']}")

        if "conversation" in test:
            response = None
            for turn in test["conversation"]:
                response = run_nl_to_sql(turn)
        else:
            response = run_nl_to_sql(test["input"])

        status = response["status"]
        metrics.update(status)

        print("Expected:", test["expected_status"])
        print("Got:", status)

    print("\n--- FINAL EVALUATION REPORT ---")
    print(metrics.report())

if __name__ == "__main__":
    run_tests()
