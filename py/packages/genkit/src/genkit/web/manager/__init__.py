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

"""Run multiple servers in a single process."""

from ._adapters import (
    ASGIServerAdapter,
    GranianAdapter,
    ServerType,
    UvicornAdapter,
)
from ._base_server import AbstractBaseServer
from ._info import get_health_info, get_server_info
from ._loop import run_loop
from ._manager import ServerManager
from ._ports import find_free_port_sync, is_port_available_sync
from ._server import Server, ServerConfig, ServerLifecycle

__all__ = [
    ASGIServerAdapter.__name__,
    AbstractBaseServer.__name__,
    find_free_port_sync.__name__,
    get_health_info.__name__,
    get_server_info.__name__,
    GranianAdapter.__name__,
    is_port_available_sync.__name__,
    run_loop.__name__,
    Server.__name__,
    ServerConfig.__name__,
    ServerLifecycle.__name__,
    ServerManager.__name__,
    ServerType.__name__,
    UvicornAdapter.__name__,
]
