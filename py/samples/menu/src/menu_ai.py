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


import os

from genkit.ai import Genkit
from genkit.plugins.dev_local_vectorstore import define_dev_local_vector_store
from genkit.plugins.google_genai import GoogleAI

if 'GEMINI_API_KEY' not in os.environ:
    print('GEMINI_API_KEY not set. Some features may not work.')
    print('To run full examples, set GEMINI_API_KEY environment variable.')
    os.environ['GEMINI_API_KEY'] = 'placeholder_key_for_dev_ui'


ai = Genkit(plugins=[GoogleAI()])

# Define dev local vector store
define_dev_local_vector_store(
    ai,
    name='menu-items',
    embedder='googleai/text-embedding-004',
)
