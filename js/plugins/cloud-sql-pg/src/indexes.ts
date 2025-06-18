/**
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

class StrategyMixin {
  operator: string;
  searchFunction: string;
  indexFunction: string;

  constructor(operator: string, searchFunction: string, indexFunction: string) {
    this.operator = operator;
    this.searchFunction = searchFunction;
    this.indexFunction = indexFunction;
  }
}

/**
 * Enumerator of the Distance strategies.
 */
export class DistanceStrategy extends StrategyMixin {
  public static EUCLIDEAN = new StrategyMixin(
    '<->',
    'l2_distance',
    'vector_l2_ops'
  );
  public static COSINE_DISTANCE = new StrategyMixin(
    '<=>',
    'cosine_distance',
    'vector_cosine_ops'
  );
  public static INNER_PRODUCT = new StrategyMixin(
    '<#>',
    'inner_product',
    'vector_ip_ops'
  );
}

/**
 * The default distance strategy used for vector comparisons.
 * @type {DistanceStrategy}
 */
export const DEFAULT_DISTANCE_STRATEGY = DistanceStrategy.COSINE_DISTANCE;

/**
 * The default suffix appended to index names.
 * @type {string}
 */
export const DEFAULT_INDEX_NAME_SUFFIX: string = 'genkitvectorindex';

/**
 * Defines the base arguments for configuring a vector index.
 */
export interface BaseIndexArgs {
  name?: string;
  distanceStrategy?: DistanceStrategy;
  partialIndexes?: string[];
}

/**
 * Abstract base class for defining vector indexes.
 */
export abstract class BaseIndex {
  name?: string;
  indexType: string;
  distanceStrategy: DistanceStrategy;
  partialIndexes?: string[];

  /**
   * Constructs a new BaseIndex instance.
   * @param {string} [name] - The optional name of the index.
   * @param {string} [indexType='base'] - The type of the index. Defaults to 'base'.
   * @param {DistanceStrategy} [distanceStrategy=DistanceStrategy.COSINE_DISTANCE] - The distance strategy. Defaults to COSINE_DISTANCE.
   * @param {string[]} [partialIndexes] - Optional array of partial index definitions.
   */
  constructor(
    name?: string,
    indexType: string = 'base',
    distanceStrategy: DistanceStrategy = DistanceStrategy.COSINE_DISTANCE,
    partialIndexes?: string[]
  ) {
    this.name = name;
    this.indexType = indexType;
    this.distanceStrategy = distanceStrategy;
    this.partialIndexes = partialIndexes;
  }

  /**
   * Set index query options for vector store initialization.
   */
  abstract indexOptions(): string;
}

/**
 * Represents an Exact Nearest Neighbor (ENN) index.
 * This index type typically performs a brute-force search.
 */
export class ExactNearestNeighbor extends BaseIndex {
  constructor(baseArgs?: BaseIndexArgs) {
    super(
      baseArgs?.name,
      'exactnearestneighbor',
      baseArgs?.distanceStrategy,
      baseArgs?.partialIndexes
    );
  }

  indexOptions(): string {
    throw new Error('indexOptions method must be implemented by subclass');
  }
}

/**
 * Represents a Hierarchical Navigable Small World (HNSW) index.
 * HNSW is an approximate nearest neighbor (ANN) algorithm.
 */
export class HNSWIndex extends BaseIndex {
  m: number;
  efConstruction: number;

  /**
   * Constructs a new HNSWIndex instance.
   * @param {BaseIndexArgs} [baseArgs] - Optional base arguments for the index.
   * @param {number} [m=16] - The 'm' parameter for HNSW. Defaults to 16.
   * @param {number} [efConstruction=64] - The 'ef_construction' parameter for HNSW. Defaults to 64.
   */
  constructor(baseArgs?: BaseIndexArgs, m?: number, efConstruction?: number) {
    super(
      baseArgs?.name,
      'hnsw',
      baseArgs?.distanceStrategy,
      baseArgs?.partialIndexes
    );
    this.m = m ?? 16;
    this.efConstruction = efConstruction ?? 64;
  }

  indexOptions(): string {
    return `(m = ${this.m}, ef_construction = ${this.efConstruction})`;
  }
}

/**
 * Represents an Inverted File Index (IVFFlat) index.
 * IVFFlat is an approximate nearest neighbor (ANN) algorithm.
 */
export class IVFFlatIndex extends BaseIndex {
  lists: number;

  /**
   * Constructs a new IVFFlatIndex instance.
   * @param {BaseIndexArgs} baseArgs - Base arguments for the index.
   * @param {number} [lists=100] - The number of lists for IVF-Flat. Defaults to 100.
   */
  constructor(baseArgs: BaseIndexArgs, lists?: number) {
    super(
      baseArgs?.name,
      'ivfflat',
      baseArgs?.distanceStrategy,
      baseArgs?.partialIndexes
    );
    this.lists = lists ?? 100;
  }

  indexOptions(): string {
    return `(lists = ${this.lists})`;
  }
}

/**
 * Convert index attributes to string.
 * Must be implemented by subclasses.
 */
export abstract class QueryOptions {
  abstract to_string(): string;
}

/**
 * Represents query options for an HNSW index.
 */
export class HNSWQueryOptions extends QueryOptions {
  efSearch: number;

  constructor(efSearch?: number) {
    super();
    this.efSearch = efSearch ?? 40;
  }

  to_string(): string {
    return `hnsw.ef_search = ${this.efSearch}`;
  }
}

/**
 * Represents query options for an IVF-Flat index.
 */
export class IVFFlatQueryOptions extends QueryOptions {
  readonly probes: number;

  constructor(probes?: number) {
    super();
    this.probes = probes ?? 1;
  }

  to_string(): string {
    return `ivflfat.probes = ${this.probes}`;
  }
}
