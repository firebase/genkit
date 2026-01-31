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

"""Vector index types and distance strategies for Cloud SQL PostgreSQL.

This module provides distance strategy enums and vector index classes
for efficient similarity search with pgvector.

Key Components
==============

┌───────────────────────────────────────────────────────────────────────────┐
│                         Index Components                                   │
├───────────────────────┬───────────────────────────────────────────────────┤
│ Component             │ Purpose                                           │
├───────────────────────┼───────────────────────────────────────────────────┤
│ DistanceStrategy      │ Enum for vector distance metrics                  │
│ BaseIndex             │ Abstract base class for vector indexes            │
│ ExactNearestNeighbor  │ Brute-force exact search (no index)               │
│ HNSWIndex             │ Hierarchical Navigable Small World index          │
│ IVFFlatIndex          │ Inverted File Index with flat quantization        │
│ QueryOptions          │ Base class for index-specific query options       │
│ HNSWQueryOptions      │ Query options for HNSW index                      │
│ IVFFlatQueryOptions   │ Query options for IVFFlat index                   │
└───────────────────────┴───────────────────────────────────────────────────┘

See Also:
    - JS Implementation: js/plugins/cloud-sql-pg/src/indexes.ts
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

DEFAULT_INDEX_NAME_SUFFIX = 'genkitvectorindex'


class DistanceStrategy(Enum):
    """Distance strategies for vector similarity search.

    Each strategy has an operator for ORDER BY, a function for computing
    distance, and an index function for creating vector indexes.

    Attributes:
        EUCLIDEAN: L2 distance - smaller is more similar.
        COSINE_DISTANCE: Cosine distance - smaller is more similar.
        INNER_PRODUCT: Inner product - larger is more similar (negated for ORDER BY).
    """

    EUCLIDEAN = ('<->', 'l2_distance', 'vector_l2_ops')
    COSINE_DISTANCE = ('<=>', 'cosine_distance', 'vector_cosine_ops')
    INNER_PRODUCT = ('<#>', 'inner_product', 'vector_ip_ops')

    def __init__(self, operator: str, search_function: str, index_function: str) -> None:
        """Initialize the distance strategy.

        Args:
            operator: SQL operator for ORDER BY (e.g., '<=>').
            search_function: SQL function name (e.g., 'cosine_distance').
            index_function: Index ops class (e.g., 'vector_cosine_ops').
        """
        self._operator = operator
        self._search_function = search_function
        self._index_function = index_function

    @property
    def operator(self) -> str:
        """Get the SQL operator for ORDER BY."""
        return self._operator

    @property
    def search_function(self) -> str:
        """Get the SQL function name for computing distance."""
        return self._search_function

    @property
    def index_function(self) -> str:
        """Get the index ops class for creating vector indexes."""
        return self._index_function


# Default distance strategy
DEFAULT_DISTANCE_STRATEGY = DistanceStrategy.COSINE_DISTANCE


@dataclass
class BaseIndexArgs:
    """Base arguments for configuring a vector index.

    Attributes:
        name: Optional name for the index.
        distance_strategy: Distance strategy to use.
        partial_indexes: Optional WHERE clause for partial index.
    """

    name: str | None = None
    distance_strategy: DistanceStrategy = DEFAULT_DISTANCE_STRATEGY
    partial_indexes: str | None = None


class BaseIndex(ABC):
    """Abstract base class for vector indexes.

    Subclasses must implement the `index_options` method to provide
    index-specific configuration options.
    """

    def __init__(
        self,
        name: str | None = None,
        index_type: str = 'base',
        distance_strategy: DistanceStrategy = DEFAULT_DISTANCE_STRATEGY,
        partial_indexes: str | None = None,
    ) -> None:
        """Initialize the base index.

        Args:
            name: Optional name for the index.
            index_type: Type of the index (e.g., 'hnsw', 'ivfflat').
            distance_strategy: Distance strategy to use.
            partial_indexes: Optional WHERE clause for partial index.
        """
        self.name = name
        self.index_type = index_type
        self.distance_strategy = distance_strategy
        self.partial_indexes = partial_indexes

    @abstractmethod
    def index_options(self) -> str:
        """Get index-specific options as SQL string.

        Returns:
            SQL string for WITH clause (e.g., '(m = 16, ef_construction = 64)').
        """
        ...


class ExactNearestNeighbor(BaseIndex):
    """Exact nearest neighbor search (no index).

    This performs brute-force search over all vectors.
    Use for small datasets or when exact results are required.
    """

    def __init__(
        self,
        name: str | None = None,
        distance_strategy: DistanceStrategy = DEFAULT_DISTANCE_STRATEGY,
        partial_indexes: str | None = None,
    ) -> None:
        """Initialize exact nearest neighbor search.

        Args:
            name: Optional name (unused for exact search).
            distance_strategy: Distance strategy to use.
            partial_indexes: Optional WHERE clause (unused for exact search).
        """
        super().__init__(
            name=name,
            index_type='exactnearestneighbor',
            distance_strategy=distance_strategy,
            partial_indexes=partial_indexes,
        )

    def index_options(self) -> str:
        """Exact search has no index options.

        Raises:
            NotImplementedError: Exact search does not use indexes.
        """
        raise NotImplementedError('ExactNearestNeighbor does not use indexes')


class HNSWIndex(BaseIndex):
    """Hierarchical Navigable Small World (HNSW) index.

    HNSW is an approximate nearest neighbor algorithm that provides
    fast query performance with good recall. Best for large datasets
    where some approximation is acceptable.

    Attributes:
        m: Maximum number of connections per node (default: 16).
        ef_construction: Size of dynamic candidate list during construction (default: 64).
    """

    def __init__(
        self,
        name: str | None = None,
        distance_strategy: DistanceStrategy = DEFAULT_DISTANCE_STRATEGY,
        partial_indexes: str | None = None,
        m: int = 16,
        ef_construction: int = 64,
    ) -> None:
        """Initialize HNSW index.

        Args:
            name: Optional name for the index.
            distance_strategy: Distance strategy to use.
            partial_indexes: Optional WHERE clause for partial index.
            m: Maximum connections per node (higher = more accurate but slower).
            ef_construction: Construction-time candidate list size (higher = better quality).
        """
        super().__init__(
            name=name,
            index_type='hnsw',
            distance_strategy=distance_strategy,
            partial_indexes=partial_indexes,
        )
        self.m = m
        self.ef_construction = ef_construction

    def index_options(self) -> str:
        """Get HNSW index options.

        Returns:
            SQL string for WITH clause.
        """
        return f'(m = {self.m}, ef_construction = {self.ef_construction})'


class IVFFlatIndex(BaseIndex):
    """Inverted File Index with flat quantization (IVFFlat).

    IVFFlat divides vectors into lists and searches a subset of lists.
    Best for large datasets when you need faster index creation than HNSW.

    Attributes:
        lists: Number of lists/clusters (default: 100).
    """

    def __init__(
        self,
        name: str | None = None,
        distance_strategy: DistanceStrategy = DEFAULT_DISTANCE_STRATEGY,
        partial_indexes: str | None = None,
        lists: int = 100,
    ) -> None:
        """Initialize IVFFlat index.

        Args:
            name: Optional name for the index.
            distance_strategy: Distance strategy to use.
            partial_indexes: Optional WHERE clause for partial index.
            lists: Number of lists to create (more lists = faster search, less recall).
        """
        super().__init__(
            name=name,
            index_type='ivfflat',
            distance_strategy=distance_strategy,
            partial_indexes=partial_indexes,
        )
        self.lists = lists

    def index_options(self) -> str:
        """Get IVFFlat index options.

        Returns:
            SQL string for WITH clause.
        """
        return f'(lists = {self.lists})'


class QueryOptions(ABC):
    """Abstract base class for index-specific query options.

    Subclasses must implement the `to_string` method to provide
    SET LOCAL statements for query optimization.
    """

    @abstractmethod
    def to_string(self) -> str:
        """Convert options to SQL SET LOCAL statement.

        Returns:
            SQL string for SET LOCAL (e.g., 'hnsw.ef_search = 40').
        """
        ...


class HNSWQueryOptions(QueryOptions):
    """Query options for HNSW index.

    Attributes:
        ef_search: Size of dynamic candidate list during search (default: 40).
    """

    def __init__(self, ef_search: int = 40) -> None:
        """Initialize HNSW query options.

        Args:
            ef_search: Search-time candidate list size (higher = better recall, slower).
        """
        self.ef_search = ef_search

    def to_string(self) -> str:
        """Get SET LOCAL statement for HNSW search.

        Returns:
            SQL SET LOCAL statement.
        """
        return f'hnsw.ef_search = {self.ef_search}'


class IVFFlatQueryOptions(QueryOptions):
    """Query options for IVFFlat index.

    Attributes:
        probes: Number of lists to search (default: 1).
    """

    def __init__(self, probes: int = 1) -> None:
        """Initialize IVFFlat query options.

        Args:
            probes: Number of lists to search (higher = better recall, slower).
        """
        self.probes = probes

    def to_string(self) -> str:
        """Get SET LOCAL statement for IVFFlat search.

        Returns:
            SQL SET LOCAL statement.
        """
        return f'ivfflat.probes = {self.probes}'
