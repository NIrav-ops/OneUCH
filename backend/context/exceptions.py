"""
Enterprise Graph Exceptions

One UCH Knowledge Graph

These exceptions are shared across:

- Graph Repository
- Graph Traversal
- Relationship Discovery
- Customer 360
- AI Graph Reasoning
"""


class GraphError(Exception):
    """
    Base graph exception.
    """
    pass


class GraphValidationError(GraphError):
    """
    Invalid graph input.
    """
    pass


class GraphTraversalError(GraphError):
    """
    Traversal failed.
    """
    pass


class GraphRepositoryError(GraphError):
    """
    Repository operation failed.
    """
    pass


class RelationshipError(GraphError):
    """
    Relationship operation failed.
    """
    pass


class BusinessObjectNotFound(GraphError):
    """
    BusinessObject could not be found.
    """
    pass


class RelationshipNotFound(GraphError):
    """
    Relationship could not be found.
    """
    pass