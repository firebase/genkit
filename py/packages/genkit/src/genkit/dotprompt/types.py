from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class PromptFileId:
    """Represents a unique identifier for a prompt file."""

    name: str
    variant: Optional[str] = None
    ns: Optional[str] = None


@dataclass
class LoadedPrompt:
    """A parsed and compiled prompt."""

    id: PromptFileId
    template: Any
    source: str
    compiled: Any | None = None
    metadata: dict[str, Any] | None = None


