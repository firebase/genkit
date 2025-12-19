"""Standalone .prompt file handling utilities (no registry integration)."""

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


