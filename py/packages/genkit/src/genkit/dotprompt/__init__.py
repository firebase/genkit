"""Standalone .prompt file handling utilities (no registry integration).

This module mirrors the JavaScript implementation's directory scanning and
file parsing behavior for `.prompt` files while intentionally avoiding any
integration with Genkit's registry. It is meant to be used by future
integration code that wires the loaded prompts into the registry.

Key behaviors aligned with JS:
  - Recursively scan a directory for `.prompt` files
  - Treat files prefixed with `_` as Handlebars partials and register them
  - Derive `name` and optional `variant` from filename: `name.variant.prompt`
  - Parse prompt source using the standalone `dotpromptz` library

Note: This module requires a `dotpromptz.Dotprompt` instance to be provided
by the caller. This keeps the implementation decoupled from the registry for
now and matches the "no integration changes yet" requirement.
"""

from typing import Any, Callable, Dict
from dotpromptz.dotprompt import Dotprompt

from .types import LoadedPrompt, PromptFileId
from .file_loader import load_prompt_dir, load_prompt_file, registry_definition_key
from .file_loader import define_partial, define_helper
from .file_loader import (
    aload_prompt_dir,
    aload_prompt_file,
    render_prompt_metadata,
)

__all__ = [
    "LoadedPrompt",
    "PromptFileId",
    "registry_definition_key",
    "load_prompt_dir",
    "load_prompt_file",
    "aload_prompt_dir",
    "aload_prompt_file",
    "render_prompt_metadata",
    "define_partial",
    "define_helper",
    "Dotprompt",
]


