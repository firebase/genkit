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

"""Shared test fakes for releasekit.

Provides reusable fake implementations of the VCS, Forge, PackageManager,
and Registry protocols so that individual test modules don't need to
duplicate boilerplate classes.

Usage::

    from tests._fakes import OK, FakeVCS, FakeForge

    vcs = FakeVCS(sha='abc123', log_lines=['aaa feat: init'])
    forge = FakeForge()
"""

from tests._fakes._forge import FakeForge as FakeForge
from tests._fakes._pm import FakePM as FakePM
from tests._fakes._registry import FakeRegistry as FakeRegistry
from tests._fakes._vcs import OK as OK, FakeVCS as FakeVCS

__all__ = [
    'OK',
    'FakeForge',
    'FakePM',
    'FakeRegistry',
    'FakeVCS',
]
