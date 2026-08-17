"""Exceptions for MemoryGraph SDK."""


class MemoryGraphError(Exception):
    """Base exception for MemoryGraph SDK."""
    pass


class ConnectionError(MemoryGraphError):
    """Raised when failing to connect to HydraDB or API backend."""
    pass


class QueryError(MemoryGraphError):
    """Raised when memory query or extraction fails."""
    pass
