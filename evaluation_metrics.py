# Computes evaluation metrics for NL → SQL system

class EvaluationMetrics:
    def __init__(self):
        self.total = 0
        self.success = 0
        self.clarification = 0
        self.errors = 0

    def update(self, status: str):
        self.total += 1

        if status == "success":
            self.success += 1
        elif status == "needs_clarification":
            self.clarification += 1
        else:
            self.errors += 1

    def report(self):
        return {
            "total_tests": self.total,
            "success_rate": round(self.success / self.total, 2),
            "clarification_rate": round(self.clarification / self.total, 2),
            "error_rate": round(self.errors / self.total, 2)
        }
