# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from typing import Union

from google.auth.credentials import Credentials
from google.genai.client import DebugConfig
from google.genai.types import HttpOptions, HttpOptionsDict
from pydantic import BaseModel, ConfigDict


class GoogleGenaiPluginOptions(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    vertexai: bool | None = (None,)
    api_key: str | None = (None,)
    credentials: Credentials | None = (None,)
    project: str | None = (None,)
    location: str | None = (None,)
    debug_config: DebugConfig | None = (None,)
    http_options: Union[HttpOptions, HttpOptionsDict] | None = (None,)
