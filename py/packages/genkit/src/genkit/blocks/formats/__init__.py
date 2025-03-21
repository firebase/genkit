# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


"""Genkit format package. Provides implementation for various formats like json, jsonl, etc."""

from genkit.blocks.formats.json import JsonFormat
from genkit.blocks.formats.types import FormatDef, Formatter, FormatterConfig


def package_name() -> str:
    """Get the fully qualified package name."""
    return 'genkit.blocks.formats'


built_in_formats = [JsonFormat()]


__all__ = [
    'package_name',
    Formatter.__name__,
    FormatDef.__name__,
    FormatterConfig.__name__,
    JsonFormat.__name__,
]
