# Copyright 2025 Google Inc.
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

from genkit.core.action import Action
from typing import Dict


class Registry:
    actions: Dict[str, Dict[str, Action]] = {}

    def register_action(self, type: str, name: str, action: Action):
        if type not in self.actions:
            self.actions[type] = {}
        self.actions[type][name] = action

    def lookup_action(self, type: str, name: str):
        if type in self.actions and name in self.actions[type]:
            return self.actions[type][name]
        return None

    def lookup_by_absolute_name(self, name: str):
        tkns = name.split('/', 2)
        return self.lookup_action(tkns[1], tkns[2])
