#!/usr/bin/env python3
#
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tests for genkit.core.constants module."""

from genkit.core.constants import (
    GENKIT_CLIENT_HEADER,
    get_client_header,
    set_client_header,
)


def test_get_client_header_default() -> None:
    """get_client_header returns the base header when no additional attribution is set."""
    set_client_header(None)

    try:
        got = get_client_header()
        if got != GENKIT_CLIENT_HEADER:
            msg = f'get_client_header() = {got!r}, want {GENKIT_CLIENT_HEADER!r}'
            raise AssertionError(msg)
    finally:
        set_client_header(None)


def test_set_and_get_client_header() -> None:
    """set_client_header appends attribution; get_client_header returns the combined value."""
    set_client_header(None)

    try:
        set_client_header('my-app/1.0')
        got = get_client_header()
        want = f'{GENKIT_CLIENT_HEADER} my-app/1.0'
        if got != want:
            msg = f'get_client_header() = {got!r}, want {want!r}'
            raise AssertionError(msg)
    finally:
        set_client_header(None)


def test_set_client_header_overwrites() -> None:
    """Calling set_client_header again replaces the previous value."""
    set_client_header(None)

    try:
        set_client_header('first')
        set_client_header('second')
        got = get_client_header()
        want = f'{GENKIT_CLIENT_HEADER} second'
        if got != want:
            msg = f'get_client_header() = {got!r}, want {want!r}'
            raise AssertionError(msg)
    finally:
        set_client_header(None)


def test_set_client_header_reset_with_none() -> None:
    """Passing None to set_client_header resets to default."""
    set_client_header('some-value')
    set_client_header(None)
    got = get_client_header()
    if got != GENKIT_CLIENT_HEADER:
        msg = f'get_client_header() = {got!r}, want {GENKIT_CLIENT_HEADER!r}'
        raise AssertionError(msg)
