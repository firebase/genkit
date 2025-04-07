# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

"""Convenience functionality to determine the running environment."""

import enum
import os
import sys

if sys.version_info < (3, 11):
    from strenum import StrEnum
else:
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
