# Copyright 2026 Google LLC
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

"""DeepSeek API client."""

from openai import OpenAI as _OpenAI


class DeepSeekClient:
    """DeepSeek API client initialization."""

    def __new__(cls, **deepseek_params) -> _OpenAI:
        """Initialize the DeepSeek client.

        Args:
            **deepseek_params: Client configuration parameters including:
                - api_key: DeepSeek API key.
                - base_url: API base URL (defaults to https://api.deepseek.com).
                - Additional OpenAI client parameters.

        Returns:
            Configured OpenAI client instance.
        """
        api_key = deepseek_params.pop('api_key')
        base_url = deepseek_params.pop('base_url', 'https://api.deepseek.com')

        return _OpenAI(api_key=api_key, base_url=base_url, **deepseek_params)
