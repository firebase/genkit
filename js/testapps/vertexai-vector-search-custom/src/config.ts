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
import { config } from 'dotenv';
config();
export const PROJECT_ID = process.env.PROJECT_ID!;
export const LOCATION = process.env.LOCATION!;

export const LOCAL_DIR = process.env.LOCAL_DIR!;

export const VECTOR_SEARCH_PUBLIC_DOMAIN_NAME =
  process.env.VECTOR_SEARCH_PUBLIC_DOMAIN_NAME!;
export const VECTOR_SEARCH_INDEX_ENDPOINT_ID =
  process.env.VECTOR_SEARCH_INDEX_ENDPOINT_ID!;
export const VECTOR_SEARCH_INDEX_ID = process.env.VECTOR_SEARCH_INDEX_ID!;
export const VECTOR_SEARCH_DEPLOYED_INDEX_ID =
  process.env.VECTOR_SEARCH_DEPLOYED_INDEX_ID!;
