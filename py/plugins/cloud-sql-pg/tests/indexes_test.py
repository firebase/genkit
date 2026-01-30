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

"""Tests for vector index types and distance strategies."""

import pytest

from genkit.plugins.cloud_sql_pg import (
    DEFAULT_DISTANCE_STRATEGY,
    DistanceStrategy,
    ExactNearestNeighbor,
    HNSWIndex,
    HNSWQueryOptions,
    IVFFlatIndex,
    IVFFlatQueryOptions,
)


class TestDistanceStrategy:
    """Tests for DistanceStrategy enum."""

    def test_euclidean_properties(self) -> None:
        """Test EUCLIDEAN distance strategy properties."""
        strategy = DistanceStrategy.EUCLIDEAN
        assert strategy.operator == '<->'
        assert strategy.search_function == 'l2_distance'
        assert strategy.index_function == 'vector_l2_ops'

    def test_cosine_distance_properties(self) -> None:
        """Test COSINE_DISTANCE strategy properties."""
        strategy = DistanceStrategy.COSINE_DISTANCE
        assert strategy.operator == '<=>'
        assert strategy.search_function == 'cosine_distance'
        assert strategy.index_function == 'vector_cosine_ops'

    def test_inner_product_properties(self) -> None:
        """Test INNER_PRODUCT strategy properties."""
        strategy = DistanceStrategy.INNER_PRODUCT
        assert strategy.operator == '<#>'
        assert strategy.search_function == 'inner_product'
        assert strategy.index_function == 'vector_ip_ops'

    def test_default_strategy_is_cosine(self) -> None:
        """Test that default strategy is COSINE_DISTANCE."""
        assert DEFAULT_DISTANCE_STRATEGY == DistanceStrategy.COSINE_DISTANCE


class TestExactNearestNeighbor:
    """Tests for ExactNearestNeighbor index."""

    def test_default_initialization(self) -> None:
        """Test default initialization."""
        index = ExactNearestNeighbor()
        assert index.index_type == 'exactnearestneighbor'
        assert index.distance_strategy == DEFAULT_DISTANCE_STRATEGY
        assert index.name is None
        assert index.partial_indexes is None

    def test_custom_initialization(self) -> None:
        """Test custom initialization."""
        index = ExactNearestNeighbor(
            name='my_exact_index',
            distance_strategy=DistanceStrategy.EUCLIDEAN,
            partial_indexes="category = 'active'",
        )
        assert index.name == 'my_exact_index'
        assert index.distance_strategy == DistanceStrategy.EUCLIDEAN
        assert index.partial_indexes == "category = 'active'"

    def test_index_options_raises(self) -> None:
        """Test that index_options raises NotImplementedError."""
        index = ExactNearestNeighbor()
        with pytest.raises(NotImplementedError):
            index.index_options()


class TestHNSWIndex:
    """Tests for HNSWIndex."""

    def test_default_initialization(self) -> None:
        """Test default initialization."""
        index = HNSWIndex()
        assert index.index_type == 'hnsw'
        assert index.m == 16
        assert index.ef_construction == 64
        assert index.distance_strategy == DEFAULT_DISTANCE_STRATEGY

    def test_custom_initialization(self) -> None:
        """Test custom initialization."""
        index = HNSWIndex(
            name='my_hnsw_index',
            distance_strategy=DistanceStrategy.INNER_PRODUCT,
            m=32,
            ef_construction=128,
        )
        assert index.name == 'my_hnsw_index'
        assert index.distance_strategy == DistanceStrategy.INNER_PRODUCT
        assert index.m == 32
        assert index.ef_construction == 128

    def test_index_options(self) -> None:
        """Test index_options returns correct SQL."""
        index = HNSWIndex(m=24, ef_construction=100)
        assert index.index_options() == '(m = 24, ef_construction = 100)'

    def test_index_options_default(self) -> None:
        """Test index_options with default values."""
        index = HNSWIndex()
        assert index.index_options() == '(m = 16, ef_construction = 64)'


class TestIVFFlatIndex:
    """Tests for IVFFlatIndex."""

    def test_default_initialization(self) -> None:
        """Test default initialization."""
        index = IVFFlatIndex()
        assert index.index_type == 'ivfflat'
        assert index.lists == 100
        assert index.distance_strategy == DEFAULT_DISTANCE_STRATEGY

    def test_custom_initialization(self) -> None:
        """Test custom initialization."""
        index = IVFFlatIndex(
            name='my_ivfflat_index',
            distance_strategy=DistanceStrategy.EUCLIDEAN,
            lists=200,
        )
        assert index.name == 'my_ivfflat_index'
        assert index.distance_strategy == DistanceStrategy.EUCLIDEAN
        assert index.lists == 200

    def test_index_options(self) -> None:
        """Test index_options returns correct SQL."""
        index = IVFFlatIndex(lists=150)
        assert index.index_options() == '(lists = 150)'

    def test_index_options_default(self) -> None:
        """Test index_options with default values."""
        index = IVFFlatIndex()
        assert index.index_options() == '(lists = 100)'


class TestHNSWQueryOptions:
    """Tests for HNSWQueryOptions."""

    def test_default_initialization(self) -> None:
        """Test default initialization."""
        options = HNSWQueryOptions()
        assert options.ef_search == 40

    def test_custom_initialization(self) -> None:
        """Test custom initialization."""
        options = HNSWQueryOptions(ef_search=100)
        assert options.ef_search == 100

    def test_to_string(self) -> None:
        """Test to_string returns correct SQL."""
        options = HNSWQueryOptions(ef_search=50)
        assert options.to_string() == 'hnsw.ef_search = 50'


class TestIVFFlatQueryOptions:
    """Tests for IVFFlatQueryOptions."""

    def test_default_initialization(self) -> None:
        """Test default initialization."""
        options = IVFFlatQueryOptions()
        assert options.probes == 1

    def test_custom_initialization(self) -> None:
        """Test custom initialization."""
        options = IVFFlatQueryOptions(probes=10)
        assert options.probes == 10

    def test_to_string(self) -> None:
        """Test to_string returns correct SQL."""
        options = IVFFlatQueryOptions(probes=5)
        assert options.to_string() == 'ivfflat.probes = 5'
