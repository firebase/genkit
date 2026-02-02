# Copyright 2026 Google LLC
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

"""Tests for Azure plugin."""

from genkit.plugins.azure import add_azure_telemetry, package_name


def test_package_name() -> None:
    """Test package_name returns correct value."""
    assert package_name() == 'genkit.plugins.azure'


def test_add_azure_telemetry_callable() -> None:
    """Test add_azure_telemetry is callable."""
    assert callable(add_azure_telemetry)


def test_add_azure_telemetry_exported() -> None:
    """Test add_azure_telemetry is exported from package."""
    from genkit.plugins.azure import add_azure_telemetry as func

    assert func is not None
    assert callable(func)
