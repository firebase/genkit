/**
 * Copyright 2024 Google LLC
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
export type SearchType = "vector" | "hybrid";

export type IndexType = "NODE" | "RELATIONSHIP";

export interface Neo4jGraphConfig {
  url: string;
  username: string;
  password: string;
  database?: string;
}

export interface Neo4jVectorConfig {
  preDeleteCollection?: boolean;
  textNodeProperty?: string;
  textNodeProperties?: string[];
  embeddingNodeProperty?: string;
  keywordIndexName?: string;
  indexName?: string;
  searchType?: SearchType;
  indexType?: IndexType;
  retrievalQuery?: string;
  nodeLabel?: string;
  createIdIndex?: boolean;
}

export class Neo4jDocument {
  text: string;
  metadata: Record<string, unknown>;
  score: number;

  constructor(text: string, 
    metadata: Record<string, unknown>, score: number) {
    this.text = text;
    this.metadata = metadata;
    this.score = score;
  }
}
