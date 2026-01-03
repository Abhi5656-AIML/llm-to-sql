# Lightweight conversation memory for follow-up queries
# Stores resolved clarifications to enrich future queries

class ConversationMemory:
    def __init__(self):
        self.context = {}

    def update(self, key: str, value: str):
        self.context[key] = value

    def apply_context(self, user_query: str) -> str:
        """
        Injects prior context into the new query.
        """
        if not self.context:
            return user_query

        context_str = " ".join(
            f"{k}: {v}" for k, v in self.context.items()
        )

        return f"{user_query}. Context: {context_str}"
