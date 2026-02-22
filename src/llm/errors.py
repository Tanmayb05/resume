"""Custom exceptions for the LLM integration layer."""


class LLMError(Exception):
    """Raised when an LLM call fails after all retry attempts.

    Attributes:
        original_error: The underlying exception that caused the failure.
        attempts: Number of attempts made before giving up.
    """

    def __init__(self, message: str, original_error: Exception | None = None, attempts: int = 0):
        super().__init__(message)
        self.original_error = original_error
        self.attempts = attempts

    def __str__(self) -> str:
        base = super().__str__()
        if self.attempts:
            base = f"{base} (after {self.attempts} attempt(s))"
        if self.original_error:
            base = f"{base}: {self.original_error}"
        return base
