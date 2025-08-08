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

// Export all of the example prompts and flows

// menu
export {
  menuIndexerFlow,
  menuRetrieveTextFlow,
  menuRetrieveVectorFlow,
} from './core/menu/menu-flows.js';
export { menuPrompt } from './core/menu/menu-prompts.js';

// crud
export { crudManagement } from './crud/crud-flows.js';
export { crudPrompt } from './crud/crud-prompts.js';

// search index
export { searchIndexManagement } from './search-index/search-index-flows.js';
export { searchIndexPrompt } from './search-index/search-index-prompts.js';

// image
export {
  imageIndexerFlow,
  imageRetrieverFlow,
} from './core/image/image-flows.js';

// document
export {
  documentIndexerFlow,
  documentRetrieverFlow,
} from './core/document/document-flows.js';
