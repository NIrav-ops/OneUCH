class AIError(Exception):
    """Base AI exception."""
    pass


class AIValidationError(AIError):
    """Raised when an AI request is invalid."""
    pass


class AIProviderError(AIError):
    """Raised when an AI provider fails."""
    pass


class AIProviderNotFoundError(AIProviderError):
    """Raised when provider is unknown."""
    pass


class AIExecutionError(AIError):
    """Raised when execution fails."""
    pass


# ------------------------------------------------------------------
# Backward compatibility aliases
# ------------------------------------------------------------------

class InvalidAIRequest(AIValidationError):
    """
    Legacy exception.
    """
    pass


class ProviderNotFound(AIProviderNotFoundError):
    """
    Legacy exception.
    """
    pass

class AIOutputValidationError(AIExecutionError):
    """
    Raised when an AI provider returns output that does not
    satisfy the response contract requested by the caller.

    Provider output is untrusted until it passes this boundary.
    """

    pass

class AIResponseParsingError(AIOutputValidationError):
    """
    Raised when validated AI output cannot be converted into
    the requested enterprise response contract.
    """

    pass