"""
Enterprise Knowledge Exceptions

All Knowledge layer exceptions inherit from KnowledgeException.

The service layer should raise these exceptions instead of generic
ValueError or Exception.
"""


class KnowledgeException(Exception):
    """Base exception for the Knowledge module."""
    pass


# ==========================================================
# Validation
# ==========================================================

class KnowledgeValidationError(KnowledgeException):
    """Raised when validation fails."""
    pass


class InvalidBusinessObject(KnowledgeValidationError):
    """Business object is invalid or missing."""
    pass


class InvalidEvidence(KnowledgeValidationError):
    """Evidence payload is invalid."""
    pass


class InvalidFact(KnowledgeValidationError):
    """Fact payload is invalid."""
    pass


# ==========================================================
# Identity
# ==========================================================

class IdentityConflict(KnowledgeException):
    """Multiple identities match the same object."""
    pass


class IdentityAlreadyExists(KnowledgeException):
    """Identity already exists."""
    pass


# ==========================================================
# Evidence
# ==========================================================

class EvidenceConflict(KnowledgeException):
    """Evidence conflicts with existing evidence."""
    pass


class EvidenceAlreadyExists(KnowledgeException):
    """Duplicate evidence."""
    pass


class EvidenceNotFound(KnowledgeException):
    """Evidence does not exist."""
    pass


# ==========================================================
# Facts
# ==========================================================

class FactConflict(KnowledgeException):
    """Fact conflicts with existing fact."""
    pass


class FactAlreadyExists(KnowledgeException):
    """Fact already exists."""
    pass


class FactNotFound(KnowledgeException):
    """Fact not found."""
    pass


# ==========================================================
# Repository
# ==========================================================

class RepositoryError(KnowledgeException):
    """Repository operation failed."""
    pass


class TransactionError(RepositoryError):
    """Database transaction failed."""
    pass