#!/usr/bin/env python3
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


"""Unit tests for the environment module."""

import os
from unittest import mock

from genkit.core.environment import (
    EnvVar,
    GenkitEnvironment,
    is_dev_environment,
)


def test_is_dev_environment() -> None:
    """Test the is_dev_environment function.

    Verifies that the is_dev_environment function correctly detects
    development environments based on environment variables.
    """
    # Test when GENKIT_ENV is not set
    with mock.patch.dict(os.environ, clear=True):
        assert not is_dev_environment()

    # Test when GENKIT_ENV is set to 'dev'
    with mock.patch.dict(
        os.environ, {EnvVar.GENKIT_ENV: GenkitEnvironment.DEV}
    ):
        assert is_dev_environment()

    # Test when GENKIT_ENV is set to something else
    with mock.patch.dict(
        os.environ, {EnvVar.GENKIT_ENV: GenkitEnvironment.PROD}
    ):
        assert not is_dev_environment()
