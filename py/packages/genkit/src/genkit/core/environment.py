# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Convenience functionality to determine the running environment."""

import os
from enum import StrEnum


class EnvVar(StrEnum):
    """Enumerates all the environment variables used by Genkit."""

    GENKIT_ENV = 'GENKIT_ENV'


class GenkitEnvironment(StrEnum):
    """Enumerates all the environments Genkit can run in."""

    DEV = 'dev'
    PROD = 'prod'


def is_dev_environment() -> bool:
    """Returns True if the current environment is a development environment.

    Returns:
        True if the current environment is a development environment.
    """
    return get_current_environment() == GenkitEnvironment.DEV


def is_prod_environment() -> bool:
    """Returns True if the current environment is a production environment.

    Returns:
        True if the current environment is a production environment.
    """
    return get_current_environment() == GenkitEnvironment.PROD


def get_current_environment() -> GenkitEnvironment:
    """Returns the current environment.

    Returns:
        The current environment.
    """
    env = os.getenv(EnvVar.GENKIT_ENV)
    if env is None:
        return GenkitEnvironment.PROD
    try:
        return GenkitEnvironment(env)
    except ValueError:
        return GenkitEnvironment.PROD
