# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
import copy
import json
import os
from abc import ABC
from functools import cached_property
from typing import Any

from genkit.plugins.dev_local_vector_store.constant import DbValue, Params
from genkit.veneer import Genkit


class LocalVectorStoreAPI(ABC):
    _LOCAL_FILESTORE_TEMPLATE = '__db_{index_name}.json'

    def __init__(self, ai: Genkit, params: Params):
        self.ai = ai
        self.params = params

    @cached_property
    def index_file_name(self):
        return self._LOCAL_FILESTORE_TEMPLATE.format(
            index_name=self.params.index_name
        )

    def _load_filestore(self) -> dict[str, DbValue]:
        data = {}
        if os.path.exists(self.index_file_name):
            with open(self.index_file_name, 'r', encoding='utf-8') as f:
                data = json.load(f)
        return self._deserialize_data(data)

    def _dump_filestore(self, data: dict[str, DbValue]) -> None:
        data = self._serialize_data(data)
        with open(self.index_file_name, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def _serialize_data(data: dict[str, DbValue]) -> dict[str, Any]:
        data = copy.deepcopy(data)
        for k in data:
            data[k] = DbValue.model_dump(data[k])
        return data

    @staticmethod
    def _deserialize_data(data: dict[str, Any]) -> dict[str, DbValue]:
        data = copy.deepcopy(data)
        for k in data:
            data[k] = DbValue.model_validate(data[k])
        return data
