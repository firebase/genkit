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


"""Base API for dev-local-vectorstore."""

import json
import os
from functools import cached_property

from .constant import DbValue


class LocalVectorStoreAPI:
    """Base class for development local vector store operations."""

    _LOCAL_FILESTORE_TEMPLATE = '__db_{index_name}.json'

    def __init__(
        self,
        index_name: str,
    ) -> None:
        """Initialize the LocalVectorStoreAPI."""
        self.index_name = index_name

    @cached_property
    def index_file_name(self) -> str:
        """Get the filename of the index file."""
        return self._LOCAL_FILESTORE_TEMPLATE.format(index_name=self.index_name)

    def _load_filestore(self) -> dict[str, DbValue]:
        data: dict[str, object] = {}
        if os.path.exists(self.index_file_name):
            with open(self.index_file_name, encoding='utf-8') as f:
                data = json.load(f)
        return self._deserialize_data(data)

    def _dump_filestore(self, data: dict[str, DbValue]) -> None:
        serialized_data = self._serialize_data(data)
        with open(self.index_file_name, 'w', encoding='utf-8') as f:
            json.dump(serialized_data, f, indent=2)

    @staticmethod
    def _serialize_data(data: dict[str, DbValue]) -> dict[str, object]:
        result: dict[str, object] = {}
        for k, v in data.items():
            result[k] = DbValue.model_dump(v, exclude_none=True)
        return result

    @staticmethod
    def _deserialize_data(data: dict[str, object]) -> dict[str, DbValue]:
        result: dict[str, DbValue] = {}
        for k, v in data.items():
            result[k] = DbValue.model_validate(v)
        return result
