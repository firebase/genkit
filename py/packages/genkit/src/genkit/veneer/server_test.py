#!/usr/bin/env python3
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


from genkit.veneer import server


def test_server_spec() -> None:
    assert (
        server.ServerSpec(scheme='http', host='localhost', port=3100).url
        == 'http://localhost:3100'
    )
