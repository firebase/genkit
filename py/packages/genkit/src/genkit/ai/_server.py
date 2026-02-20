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

"""Functionality used by the Genkit veneer to start multiple servers.

The following servers may be started depending upon the host environment:

- Reflection API server.
- Flows server.

The reflection API server is started only in dev mode, which is enabled by the
setting the environment variable `GENKIT_ENV` to `dev`. By default, the
reflection API server binds and listens on (localhost, 3100 or the next available
port).  The flows server is the production servers that exposes flows and actions
over HTTP.
"""

from dataclasses import dataclass

from genkit.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ServerSpec:
    """ServerSpec encapsulates the scheme, host and port information.

    This class defines the server binding and listening configuration.
    """

    port: int
    scheme: str = 'http'
    host: str = 'localhost'

    @property
    def url(self) -> str:
        """URL evaluates to the host base URL given the server specs."""
        return f'{self.scheme}://{self.host}:{self.port}'
