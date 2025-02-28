# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from collections.abc import Callable

from pydantic import BaseModel

ToolFn = Callable[[BaseModel], BaseModel]
