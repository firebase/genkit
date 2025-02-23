# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.

import json
from typing import Any

from pydantic import BaseModel


def dump_json(obj: Any):
    if isinstance(obj, BaseModel):
        return obj.model_dump_json(by_alias=True)
    else:
        return json.dumps(obj)
