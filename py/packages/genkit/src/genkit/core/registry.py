# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


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
