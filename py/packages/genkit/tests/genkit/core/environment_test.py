#!/usr/bin/env python3
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


"""Unit tests for the environment module."""

import os
from unittest import mock

from genkit.core.environment import (
    EnvVar,
    GenkitEnvironment,
    get_current_environment,
    is_dev_environment,
    is_prod_environment,
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
    with mock.patch.dict(os.environ, {EnvVar.GENKIT_ENV: GenkitEnvironment.DEV}):
        assert is_dev_environment()

    # Test when GENKIT_ENV is set to something else
    with mock.patch.dict(os.environ, {EnvVar.GENKIT_ENV: GenkitEnvironment.PROD}):
        assert not is_dev_environment()


def test_is_prod_environment() -> None:
    """Test the is_prod_environment function.

    Verifies that the is_prod_environment function correctly detects
    production environments based on environment variables.
    """
    # Test when GENKIT_ENV is not set
    with mock.patch.dict(os.environ, clear=True):
        assert is_prod_environment()

    # Test when GENKIT_ENV is set to 'prod'
    with mock.patch.dict(os.environ, {EnvVar.GENKIT_ENV: GenkitEnvironment.PROD}):
        assert is_prod_environment()

    # Test when GENKIT_ENV is set to something else
    with mock.patch.dict(os.environ, {EnvVar.GENKIT_ENV: GenkitEnvironment.DEV}):
        assert not is_prod_environment()


def test_get_current_environment() -> None:
    """Test the get_current_environment function.

    Verifies that the get_current_environment function correctly returns
    the current environment based on environment variables.
    """
    # Test when GENKIT_ENV is not set
    with mock.patch.dict(os.environ, clear=True):
        assert get_current_environment() == GenkitEnvironment.PROD

    # Test when GENKIT_ENV is set to 'prod'
    with mock.patch.dict(os.environ, {EnvVar.GENKIT_ENV: GenkitEnvironment.PROD}):
        assert get_current_environment() == GenkitEnvironment.PROD

    # Test when GENKIT_ENV is set to 'dev'
    with mock.patch.dict(os.environ, {EnvVar.GENKIT_ENV: GenkitEnvironment.DEV}):
        assert get_current_environment() == GenkitEnvironment.DEV

    # Test when GENKIT_ENV is set to something else
    with mock.patch.dict(os.environ, {EnvVar.GENKIT_ENV: 'invalid'}):
        assert get_current_environment() == GenkitEnvironment.PROD
