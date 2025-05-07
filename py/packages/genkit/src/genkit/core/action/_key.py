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

"""Action key module for defining and managing action keys."""

from .types import ActionKind


def parse_action_key(key: str) -> tuple[ActionKind, str]:
    """Parse an action key into its kind and name components.

    Args:
        key: The action key to parse, in the format "/kind/name".

    Returns:
        A tuple containing the ActionKind and name.

    Raises:
        ValueError: If the key format is invalid or if the kind is not a valid
            ActionKind.
    """
    tokens = key.split('/')
    if len(tokens) < 3 or not tokens[1] or not tokens[2]:
        msg = f'Invalid action key format: `{key}`.Expected format: `/<kind>/<name>`'
        raise ValueError(msg)

    kind_str = tokens[1]
    name = '/'.join(tokens[2:])
    try:
        kind = ActionKind(kind_str)
    except ValueError as e:
        msg = f'Invalid action kind: `{kind_str}`'
        raise ValueError(msg) from e
    return kind, name


def create_action_key(kind: ActionKind, name: str) -> str:
    """Create an action key from its kind and name components.

    Args:
        kind: The kind of action.
        name: The name of the action.

    Returns:
        The action key in the format `/<kind>/<name>`.
    """
    return f'/{kind}/{name}'
