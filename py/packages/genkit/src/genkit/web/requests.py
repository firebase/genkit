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

"""Helper functions for reading JSON request bodies."""

from starlette.datastructures import QueryParams
from starlette.requests import Request


def is_streaming_requested(request: Request) -> bool:
    """Check if streaming is requested.

    Streaming is requested if the query parameter 'stream' is set to 'true' or
    if the Accept header is 'text/event-stream'.

    Args:
        request: Starlette request object.

    Returns:
        True if streaming is requested, False otherwise.
    """
    by_header = request.headers.get('accept', '') == 'text/event-stream'
    by_query = is_query_flag_enabled(request.query_params, 'stream')
    return by_header or by_query


def is_query_flag_enabled(query_params: QueryParams, flag: str) -> bool:
    """Check if a query flag is enabled.

    Args:
        query_params: Dictionary containing parsed query parameters.
        flag: Flag name to check.

    Returns:
        True if the query flag is enabled, False otherwise.
    """
    return query_params.get(flag, ['false'])[0] == 'true'
