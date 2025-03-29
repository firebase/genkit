"""Deprecation utilities.

This module provides utilities for deprecating models and other resources.
"""

import enum
import warnings


def deprecate_models(deprecated_map: dict[str, str | None]) -> type:
    """Create a metaclass for handling deprecated enum values.

    Example:
        >>> DEPRECATED_MODELS = {
            'GEMINI_1_0_PRO': 'GEMINI_2_0_PRO',
            'GEMINI_1_5_PRO': 'GEMINI_2_0_PRO',
            'GEMINI_1_5_FLASH': 'GEMINI_2_0_FLASH',
            'GEMINI_1_5_FLASH_8B': None,
        }
        >>> class GeminiVersion(
                enum.StrEnum, metaclass=deprecate_models(DEPRECATED_MODELS)
        ):
            GEMINI_1_0_PRO = 'gemini-1.0-pro'
            GEMINI_1_5_FLASH = 'gemini-1.5-flash'
            GEMINI_1_5_FLASH_8B = 'gemini-1.5-flash-8b'
            GEMINI_1_5_PRO = 'gemini-1.5-pro'
            GEMINI_2_0_FLASH = 'gemini-2.0-flash'
            GEMINI_2_0_PRO = 'gemini-2.0-pro'

        >>> GeminiVersion.GEMINI_1_0_PRO
        Traceback (most recent call last):
        ...
        DeprecationWarning: GEMINI_1_0_PRO is deprecated; use GEMINI_2_0_PRO instead
        >>> GeminiVersion.GEMINI_2_0_FLASH
        'gemini-2.0-flash'
        >>> GeminiVersion.GEMINI_2_0_PRO
        'gemini-2.0-pro'


    Args:
        deprecated_map: Dict mapping enum names to their recommended
            replacements.  If value is None, no replacement is suggested.

    Returns:
        An EnumMeta subclass that warns on deprecated value access with
        recommendations.
    """

    class DeprecatedEnumMeta(enum.EnumMeta):
        def __getattribute__(cls, name: str) -> str:
            if name in deprecated_map:
                recommendation = deprecated_map[name]
                message = (
                    f'{name} is deprecated; use {recommendation} instead'
                    if recommendation
                    else f'{name} is deprecated'
                )
                warnings.warn(
                    message,
                    DeprecationWarning,
                    stacklevel=2,
                )
            return super().__getattribute__(name)

    return DeprecatedEnumMeta
