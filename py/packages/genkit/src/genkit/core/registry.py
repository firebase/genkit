# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


"""The registry is used to store and lookup resources."""

from typing import Dict
from genkit.core.action import Action


class Registry:
    """Stores actions, trace stores, flow state stores, plugins, and schemas."""

    actions: Dict[str, Dict[str, Action]] = {}

    def register_action(self, action_type: str, name: str, action: Action):
        if action_type not in self.actions:
            self.actions[action_type] = {}
        self.actions[action_type][name] = action

    def lookup_action(self, action_type: str, name: str):
        if action_type in self.actions and name in self.actions[action_type]:
            return self.actions[action_type][name]
        return None

    def lookup_by_absolute_name(self, name: str):
        tkns = name.split('/', 2)
        return self.lookup_action(tkns[1], tkns[2])
