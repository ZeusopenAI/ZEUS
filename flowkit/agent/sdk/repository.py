"""Re-export Repository from the persistence layer for backward-compatible imports."""

from agent.sdk.persistence.base import Repository
from agent.sdk.persistence.sqlite_repository import SQLiteRepository

__all__ = ["Repository", "SQLiteRepository"]
