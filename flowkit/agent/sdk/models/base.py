"""Base class for repo-backed SDK domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from agent.sdk.repository import Repository


@dataclass
class DomainModel:
    """Base for all SDK domain models.

    Provides ``_repo`` for persistence and ``save()`` / ``reload()`` helpers.
    Subclasses set ``_table`` at the class level so the repo knows which
    DB table to target.
    """

    id: str = ""
    _repo: Optional[Any] = field(default=None, repr=False, compare=False)
    _table: str = field(default="", init=False, repr=False, compare=False)

    async def save(self, **overrides: Any) -> None:
        """Persist current field values (plus *overrides*) via the repo."""
        if self._repo is None:
            raise RuntimeError("No repository attached — cannot save")
        await self._repo.update(self._table, self.id, **overrides)
        for k, v in overrides.items():
            if hasattr(self, k):
                object.__setattr__(self, k, v)

    async def reload(self) -> None:
        """Re-read this object's row from the DB and refresh local fields."""
        if self._repo is None:
            raise RuntimeError("No repository attached — cannot reload")
        row = await self._repo.get(self._table, self.id)
        if row is None:
            raise LookupError(f"{self._table} {self.id} not found")
        for k, v in row.items():
            if hasattr(self, k) and not k.startswith("_"):
                object.__setattr__(self, k, v)
