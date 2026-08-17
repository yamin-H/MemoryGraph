"""MemoryGraph: Graph-native agent memory layer on HydraDB.

A temporal knowledge graph memory system with recursive SUPERSEDES edges,
multi-hop entity reasoning, and calibrated honest abstention.
"""

from memorygraph.client import MemoryGraph
from memorygraph.exceptions import ConnectionError, MemoryGraphError, QueryError
from memorygraph.models import MemoryResult, Message

__version__ = "0.1.0"
__all__ = [
    "MemoryGraph",
    "MemoryResult",
    "Message",
    "MemoryGraphError",
    "ConnectionError",
    "QueryError",
]
