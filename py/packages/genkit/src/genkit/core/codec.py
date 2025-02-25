# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.

import json
from typing import Any

from pydantic import BaseModel


def dump_json(obj: Any) -> str:
    """Dumps an object to a JSON string.

    If the object is a Pydantic BaseModel, it will be dumped using the
    model_dump_json method using the by_alias flag set to True.  Otherwise, the
    object will be dumped using the json.dumps method.

    Args:
        obj: The object to dump.

    Returns:
        A JSON string.
    """
    if isinstance(obj, BaseModel):
        return obj.model_dump_json(by_alias=True)
    else:
        return json.dumps(obj)
