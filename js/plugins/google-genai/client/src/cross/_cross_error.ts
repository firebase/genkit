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

export function crossError(): Error {
  // TODO(b/399934880): this message needs a link to a help page explaining how to enable conditional exports
  return new Error(`This feature requires the web or Node specific @google/genai implementation, you can fix this by either:

*Enabling conditional exports for your project [recommended]*

*Using a platform specific import* - Make sure your code imports either '@google/genai/web' or '@google/genai/node' instead of '@google/genai'.
`);
}
