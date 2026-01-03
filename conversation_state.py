# Manages unresolved queries and conversation context
# Ensures clarification is resolved BEFORE SQL generation

class ConversationState:
    def __init__(self):
        self.pending_query = None
        self.pending_question = None
        self.resolved_context = {}

    def set_pending(self, query: str, question: str = None):
        self.pending_query = query
        self.pending_question = question

    def has_pending(self) -> bool:
        return self.pending_query is not None

    def get_pending_query(self) -> str:
        return self.pending_query

    def get_pending_question(self) -> str:
        return self.pending_question

    def is_same_pending(self, user_query: str) -> bool:
        if not self.pending_query:
            return False
        return user_query.strip().lower() == self.pending_query.strip().lower()

    def reset_pending(self):
        self.pending_query = None
        self.pending_question = None

    def resolve_pending(self, clarification: str) -> str:
        """
        Combines the original ambiguous query with user clarification and clears pending state.
        """
        full_query = f"{self.pending_query} {clarification}"
        self.reset_pending()
        return full_query
