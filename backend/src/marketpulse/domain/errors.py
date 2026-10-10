"""Domain-level errors shared across provider implementations."""


class ProviderFailure(Exception):
    def __init__(self, category: str):
        self.category = category
        super().__init__(category)
