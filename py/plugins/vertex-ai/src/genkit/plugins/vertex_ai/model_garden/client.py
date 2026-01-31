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


"""Vertex AI client."""

import google.auth.transport.requests
from google import auth
from openai import OpenAI as _OpenAI


class OpenAIClient:
    """Handles OpenAI API client Initialization."""

    def __new__(cls, **openai_params: object) -> _OpenAI:
        """Initializes the OpenAIClient based on the plugin source."""
        location = openai_params.get('location')
        project_id = openai_params.get('project_id')
        if project_id:
            credentials, _ = auth.default()
        else:
            credentials, project_id = auth.default()

        credentials.refresh(google.auth.transport.requests.Request())
        base_url = f'https://{location}-aiplatform.googleapis.com/v1beta1/projects/{project_id}/locations/{location}/endpoints/openapi'
        return _OpenAI(api_key=credentials.token, base_url=base_url)
