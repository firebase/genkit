# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.

import json
from typing import Any

from pydantic import BaseModel


def dump_dict(obj: Any):
    """Converts an object to a dictionary, handling Pydantic BaseModel instances specially.

    If the input object is a Pydantic BaseModel, it returns a dictionary representation
    of the model, excluding fields with `None` values and using aliases for field names.
    For any other object type, it returns the object unchanged.

    Args:
        obj: The object to potentially convert to a dictionary.

    Returns:
        A dictionary if the input is a Pydantic BaseModel, otherwise the original object.
    """
    if isinstance(obj, BaseModel):
        return obj.model_dump(exclude_none=True, by_alias=True)
    else:
        return obj


def dump_json(obj: Any, indent=None) -> str:
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
        return obj.model_dump_json(
            by_alias=True, exclude_none=True, indent=indent
        )
    else:
        return json.dumps(obj)
