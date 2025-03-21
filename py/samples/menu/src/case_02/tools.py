# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

import json
import os

from menu_ai import ai
from menu_schemas import MenuToolOutputSchema

menu_json_path = os.path.join('..', '..', 'data', 'menu.json')
with open(menu_json_path, 'r') as f:
    menu_data = json.load(f)


@ai.tool(
    description="Use this tool to retrieve all the items on today's menu",
    name='todaysMenu',
)
def menu_tool() -> MenuToolOutputSchema:
    return MenuToolOutputSchema(
        menu_data=menu_data,
    )
