# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel


class GoogleAiPluginOptions(BaseModel):
    api_key: str | None = None
    # TODO: implement all authentication methods
    # project: Optional[str] = None,
    # location: Optional[str] = None
    # TODO: implement http options
    # api_version: Optional[str] = None
    # base_url: Optional[str] = None
