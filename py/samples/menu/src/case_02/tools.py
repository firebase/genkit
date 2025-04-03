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


import json
import os

from menu_ai import ai
from menu_schemas import MenuToolOutputSchema

menu_json_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'menu.json')
with open(menu_json_path) as f:
    menu_data = json.load(f)


@ai.tool(name='menu_tool')
def menu_tool(input=None) -> MenuToolOutputSchema:
    """Use this tool to retrieve all the items on today's menu."""
    return MenuToolOutputSchema(
        menu_data=menu_data,
    )
