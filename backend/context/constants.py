"""
Enterprise Graph Constants

One UCH Knowledge Graph

Centralized graph-related constants used across:

- Graph Repository
- Graph Traversal
- Relationship Discovery
- Customer 360
- AI Graph Reasoning
"""


# ----------------------------------------------------
# Traversal Defaults
# ----------------------------------------------------

DEFAULT_MAX_DEPTH = 3

MAX_GRAPH_DEPTH = 20

DEFAULT_SHORTEST_PATH_DEPTH = 10


# ----------------------------------------------------
# Confidence
# ----------------------------------------------------

MAX_CONFIDENCE = 100

MIN_CONFIDENCE = 0


# ----------------------------------------------------
# Relationship
# ----------------------------------------------------

DEFAULT_RELATIONSHIP_TYPE = "RELATED_TO"

DEFAULT_RELATIONSHIP_DIRECTION = "BIDIRECTIONAL"


# ----------------------------------------------------
# Cache
# ----------------------------------------------------

GRAPH_CACHE_TIMEOUT = 300


# ----------------------------------------------------
# Discovery
# ----------------------------------------------------

MAX_DISCOVERY_OBJECTS = 1000