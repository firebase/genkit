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

import { ModelArmorClient } from '@google-cloud/modelarmor';
import { GenkitError } from 'genkit';
import {
  GenerateRequest,
  GenerateResponseData,
  ModelMiddleware,
  Part,
} from 'genkit/model';
import { runInNewSpan } from 'genkit/tracing';

export interface ModelArmorOptions {
  templateName: string;
  client?: ModelArmorClient;
  /**
   * Options for the Model Armor client (e.g. apiEndpoint).
   */
  clientOptions?: any;
  /**
   * What to sanitize. Defaults to 'all'.
   */
  protectionTarget?: 'all' | 'userPrompt' | 'modelResponse';
  /**
   * Whether to block on SDP match even if the content was successfully de-identified.
   * Defaults to false (lenient).
   */
  strictSdpEnforcement?: boolean;
  /**
   * List of filters to enforce. If not specified, all filters are enforced.
   * Possible values: 'rai', 'pi_and_jailbreak', 'malicious_uris', 'csam', 'sdp'.
   */
  filters?: (
    | 'rai'
    | 'pi_and_jailbreak'
    | 'malicious_uris'
    | 'csam'
    | 'sdp'
    | (string & {})
  )[];
}

function extractText(parts: Part[]): string {
  return parts.map((p) => p.text || '').join('');
}

function applySdp(
  content: Part[],
  result: any
): { sdpApplied: boolean; content: Part[] } {
  const sdpResult =
    result.filterResults?.['sdp']?.sdpFilterResult?.deidentifyResult;

  if (sdpResult && sdpResult.data?.text) {
    const nonTextParts = content.filter((p) => !p.text);
    return {
      sdpApplied: true,
      content: [...nonTextParts, { text: sdpResult.data.text }],
    };
  }
  return { sdpApplied: false, content };
}

function shouldBlock(
  result: any,
  options: ModelArmorOptions,
  sdpApplied: boolean
): boolean {
  if (result.filterMatchState !== 'MATCH_FOUND') {
    return false;
  }
  // Check if we should block.
  // If strict SDP enforcement is enabled and SDP was applied, we must block.
  if (options.strictSdpEnforcement && sdpApplied) {
    return true;
  }
  // Otherwise, check if any active filter matched.
  if (result.filterResults) {
    for (const [key, filterResult] of Object.entries(result.filterResults)) {
      if (options.filters && !options.filters.includes(key)) continue;
      if (key === 'sdp' && sdpApplied) continue;

      // Look for matchState in the nested object
      // e.g. filterResult.raiFilterResult.matchState
      const nestedResult = Object.values(filterResult as any)[0] as any;
      if (nestedResult?.matchState === 'MATCH_FOUND') {
        return true;
      }
    }
  }
  return false;
}

async function sanitizeUserPrompt(
  req: GenerateRequest,
  client: ModelArmorClient,
  options: ModelArmorOptions
) {
  let targetMessageIndex = -1;
  // Find the last user message to sanitize
  for (let i = req.messages.length - 1; i >= 0; i--) {
    if (req.messages[i].role === 'user') {
      targetMessageIndex = i;
      break;
    }
  }

  if (targetMessageIndex !== -1) {
    const userMessage = req.messages[targetMessageIndex];
    const promptText = extractText(userMessage.content);

    if (promptText) {
      await runInNewSpan(
        { metadata: { name: 'sanitizeUserPrompt' } },
        async (meta) => {
          meta.input = {
            name: options.templateName,
            userPromptData: {
              text: promptText,
            },
          };
          const [response] = await client.sanitizeUserPrompt({
            name: options.templateName,
            userPromptData: {
              text: promptText,
            },
          });
          meta.output = response;

          if (response.sanitizationResult) {
            const result = response.sanitizationResult;
            const { sdpApplied, content } = applySdp(
              userMessage.content,
              result
            );
            if (sdpApplied) {
              req.messages[targetMessageIndex].content = content;
            }

            if (shouldBlock(result, options, sdpApplied)) {
              throw new GenkitError({
                status: 'PERMISSION_DENIED',
                message: 'Model Armor blocked user prompt.',
                detail: result,
              });
            }
          }
        }
      );
    }
  }
}

async function sanitizeModelResponse(
  response: GenerateResponseData,
  client: ModelArmorClient,
  options: ModelArmorOptions
) {
  const candidates = response.message
    ? [{ index: 0, message: response.message, finishReason: 'stop' }]
    : response.candidates || [];

  for (const candidate of candidates) {
    const modelText = extractText(candidate.message.content);

    if (modelText) {
      await runInNewSpan(
        { metadata: { name: 'sanitizeModelResponse' } },
        async (meta) => {
          meta.input = {
            name: options.templateName,
            modelResponseData: {
              text: modelText,
            },
          };
          const [response] = await client.sanitizeModelResponse({
            name: options.templateName,
            modelResponseData: {
              text: modelText,
            },
          });
          meta.output = response;

          if (response.sanitizationResult) {
            const result = response.sanitizationResult;
            const { sdpApplied, content } = applySdp(
              candidate.message.content,
              result
            );
            if (sdpApplied) {
              candidate.message.content = content;
            }

            if (shouldBlock(result, options, sdpApplied)) {
              throw new GenkitError({
                status: 'PERMISSION_DENIED',
                message: 'Model Armor blocked model response.',
                detail: result,
              });
            }
          }
        }
      );
    }
  }
}

/**
 * Model Middleware that uses Google Cloud Model Armor to sanitize user prompts and model responses.
 */
export function modelArmor(options: ModelArmorOptions): ModelMiddleware {
  const client = options.client || new ModelArmorClient(options.clientOptions);
  const protectionTarget = options.protectionTarget ?? 'all';
  const protectUserPrompt =
    protectionTarget === 'all' || protectionTarget === 'userPrompt';
  const protectModelResponse =
    protectionTarget === 'all' || protectionTarget === 'modelResponse';

  return async (req, next) => {
    // 1. Sanitize User Prompt
    if (protectUserPrompt) {
      await sanitizeUserPrompt(req, client, options);
    }

    // 2. Call Model
    const response = await next(req);

    // 3. Sanitize Model Response
    if (protectModelResponse) {
      await sanitizeModelResponse(response, client, options);
    }

    return response;
  };
}
