from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple
from dotpromptz.dotprompt import Dotprompt

from .types import LoadedPrompt, PromptFileId


# TODO: Confirm canonical namespace rules when scanning nested directories.
def registry_definition_key(name: str, variant: str | None = None, ns: str | None = None) -> str:
    """Build a definition key "ns/name.variant" where ns/variant are optional."""
    prefix = f"{ns}/" if ns else ""
    suffix = f".{variant}" if variant else ""
    return f"{prefix}{name}{suffix}"


def _parse_name_and_variant(filename: str) -> Tuple[str, str | None]:
    """Extract base name and optional variant from a `.prompt` filename.

    Behavior:
      - strip `.prompt`
      - if remaining contains a `.` split name and variant at the first dot
    """
    base = filename[:-7] if filename.endswith('.prompt') else filename
    if '.' in base:
        parts = base.split('.')
        return parts[0], parts[1]
    return base, None


def define_partial(dp: Dotprompt, name: str, source: str) -> None:
    """Register a Handlebars partial with the provided `Dotprompt` instance."""
    # Support both camelCase and snake_case for Python bindings.
    if hasattr(dp, 'definePartial'):
        getattr(dp, 'definePartial')(name, source)  # type: ignore[attr-defined]
    else:
        getattr(dp, 'define_partial')(name, source)


def define_helper(dp: Dotprompt, name: str, fn: Any) -> None:
    """Register a helper on the provided `Dotprompt` instance."""
    dp.defineHelper(name, fn)


def load_prompt_file(dp: Dotprompt, file_path: str, ns: str | None = None) -> LoadedPrompt:
    """Load and parse a single `.prompt` file using dotpromptz.

    - Reads file as UTF-8
    - Parses source via `dp.parse`
    - Does NOT eagerly compile; compilation can be done by caller
    - Returns a LoadedPrompt instance
    """
    path = Path(file_path)
    source = path.read_text(encoding='utf-8')
    template = dp.parse(source)
    name, variant = _parse_name_and_variant(path.name)
    return LoadedPrompt(
        id=PromptFileId(name=name, variant=variant, ns=ns),
        template=template,
        source=source,
    )


async def render_prompt_metadata(dp: Dotprompt, loaded: LoadedPrompt) -> dict[str, Any]:
    """Render metadata for a parsed template using dotpromptz.

    Performs cleanup for null schema descriptions.
    """
    # Support both camelCase and snake_case for Python bindings.
    if hasattr(dp, 'renderMetadata'):
        metadata: dict[str, Any] = await getattr(dp, 'renderMetadata')(loaded.template)  # type: ignore[attr-defined]
    else:
        metadata = await getattr(dp, 'render_metadata')(loaded.template)

    # Remove null descriptions
    try:
        if metadata.get('output', {}).get('schema', {}).get('description', None) is None:
            metadata['output']['schema'].pop('description', None)
    except Exception:
        pass
    try:
        if metadata.get('input', {}).get('schema', {}).get('description', None) is None:
            metadata['input']['schema'].pop('description', None)
    except Exception:
        pass

    loaded.metadata = metadata
    return metadata


def _iter_prompt_dir(dir_path: str) -> Iterable[Tuple[Path, str]]:
    """Yield (path, subdir) for files under dir recursively.

    subdir is the relative directory from the root, used for namespacing.
    """
    root = Path(dir_path).resolve()
    for current_dir, _dirs, files in os.walk(root):
        rel = os.path.relpath(current_dir, root)
        subdir = '' if rel == '.' else rel
        for fname in files:
            if fname.endswith('.prompt'):
                yield Path(current_dir) / fname, subdir


def load_prompt_dir(dp: Dotprompt, dir_path: str, ns: str | None = None) -> Dict[str, LoadedPrompt]:
    """Recursively scan a directory, registering partials and loading prompts.

    - Files starting with `_` are treated as partials; register via definePartial
    - Other `.prompt` files are parsed and returned
    - If a file is in a subdirectory, that subdirectory is prefixed to the prompt name
      using the definition key semantics ("ns/subdir/name.variant")

    Returns a dict mapping definition keys to `LoadedPrompt`.
    """
    loaded: Dict[str, LoadedPrompt] = {}
    for file_path, subdir in _iter_prompt_dir(dir_path):
        fname = file_path.name
        parent = file_path.parent
        if fname.startswith('_') and fname.endswith('.prompt'):
            partial_name = fname[1:-7]
            define_partial(dp, partial_name, (parent / fname).read_text(encoding='utf-8'))
            continue

        # Regular prompt file
        name, variant = _parse_name_and_variant(fname)

        # Include subdir in the prompt "name" prefix, not in ns.
        name_with_prefix = f"{subdir}/{name}" if subdir else name

        loaded_prompt = load_prompt_file(dp, str(file_path), ns=ns)
        # Update the id.name to include the subdir prefix.
        loaded_prompt.id = PromptFileId(name=name_with_prefix, variant=variant, ns=ns)

        key = registry_definition_key(name_with_prefix, variant, ns)
        loaded[key] = loaded_prompt
    return loaded


async def aload_prompt_file(dp: Dotprompt, file_path: str, ns: str | None = None, *, with_metadata: bool = True) -> LoadedPrompt:
    """Async variant that also renders metadata when requested."""
    loaded = load_prompt_file(dp, file_path, ns)
    if with_metadata:
        await render_prompt_metadata(dp, loaded)
    return loaded


async def aload_prompt_dir(dp: Dotprompt, dir_path: str, ns: str | None = None, *, with_metadata: bool = True) -> Dict[str, LoadedPrompt]:
    """Async directory loader that optionally renders metadata for each prompt."""
    loaded = load_prompt_dir(dp, dir_path, ns)
    if with_metadata:
        for key, prompt in loaded.items():
            await render_prompt_metadata(dp, prompt)
    return loaded


