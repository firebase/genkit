from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class PromptFileId:
    """Represents a unique identifier for a prompt file.

    Matches the JS key composition logic using `registryDefinitionKey`:
    "ns/name.variant" where `ns` and `variant` are optional.

    Note: Integration code will decide the final key string; this structure
    simply preserves fields so that integration can build the key.
    """

    name: str
    variant: Optional[str] = None
    ns: Optional[str] = None


@dataclass
class LoadedPrompt:
    """A parsed and compiled prompt.

    - `id`: Parsed identifier components (name, variant, ns).
    - `template`: The parsed template AST or representation returned by dotpromptz.parse.
    - `source`: The raw file contents.
    - `metadata`: Metadata produced by dotpromptz.renderMetadata (optional).

    Notes:
    - We intentionally keep this structure minimal and close to JS behavior.
    - `compiled` is optional to allow lazy compilation as in JS (loaded on first use).
    """

    id: PromptFileId
    template: Any
    source: str
    compiled: Any | None = None
    metadata: dict[str, Any] | None = None


