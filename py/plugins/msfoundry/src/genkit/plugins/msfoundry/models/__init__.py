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

"""Microsoft Foundry model implementations.

See: https://ai.azure.com/catalog/models
"""

from .model import MSFoundryModel
from .model_info import (
    MODELS_SUPPORTING_RESPONSE_FORMAT,
    SUPPORTED_EMBEDDING_MODELS,
    SUPPORTED_MSFOUNDRY_MODELS,
    get_model_info,
)

__all__ = [
    'MSFoundryModel',
    'SUPPORTED_MSFOUNDRY_MODELS',
    'SUPPORTED_EMBEDDING_MODELS',
    'MODELS_SUPPORTING_RESPONSE_FORMAT',
    'get_model_info',
]
