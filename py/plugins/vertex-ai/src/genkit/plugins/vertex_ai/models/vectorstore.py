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

import sys

if sys.version_info < (3, 11):  # noqa
    from strenum import StrEnum  # noqa
else:  # noqa
    from enum import StrEnum  # noqa

from pydantic import BaseModel, Field


class IndexShardSize(StrEnum):
    """Defines the size of each shard in the index."""
    SMALL = 'SHARD_SIZE_SMALL'
    MEDIUM = 'SHARD_SIZE_MEDIUM'
    LARGE = 'SHARD_SIZE_LARGE'


class FeatureNormType(StrEnum):
    """Specifies the normalization applied to feature vectors."""
    NONE = 'NONE'
    UNIT_L2_NORMALIZED = 'UNIT_L2_NORM'


class DistanceMeasureType(StrEnum):
    """Defines the available distance measure methods."""
    SQUARED_L2 = 'SQUARED_L2_DISTANCE'
    L2 = 'L2_DISTANCE'
    COSINE = 'COSINE_DISTANCE'
    DOT_PRODUCT = 'DOT_PRODUCT_DISTANCE'


class IndexConfig(BaseModel):
    """Defines the configurations of indexes."""
    dimensions: int = 128
    approximate_neighbors_count: int = Field(default=100, alias='approximateNeighborsCount')
    distance_measure_type: DistanceMeasureType | str = Field(
        default=DistanceMeasureType.COSINE, alias='distanceMeasureType'
    )
    feature_norm_type: FeatureNormType | str = Field(default=FeatureNormType.NONE, alias='featureNormType')
    shard_size: IndexShardSize | str = Field(default=IndexShardSize.MEDIUM, alias='shardSize')
    algorithm_config: dict | None = Field(default=None, alias='algorithmConfig')
