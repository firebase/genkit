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

import {
  Action,
  ActionContext,
  defineAction,
  GenkitError,
  z,
} from '@genkit-ai/core';
import { Registry } from '@genkit-ai/core/registry';
import uriTemplate from 'uri-templates';
import { Part, PartSchema } from './model.js';

/**
 * Options for defining a resource.
 */
export interface ResourceOptions {
  /**
   * The URI of the resource. Can contain template variables.
   */
  uri?: string;

  /**
   * The URI tempalate (ex. `my://resource/{id}`). See RFC6570 for specification.
   */
  template?: string;

  /**
   * A description of the resource.
   */
  description?: string;
}

/**
 * A function that returns parts for a given resource.
 */
export type ResourceFn = (
  vars: Record<string, string>,
  ctx: ActionContext
) => Part[] | Promise<Part[]>;

/**
 * A resource action.
 */
export interface ResourceAction
  extends Action<
    z.ZodString,
    z.ZodArray<typeof PartSchema>,
    z.ZodArray<typeof PartSchema>
  > {
  matches(input: string): boolean;
}

/**
 * Defines a resource.
 *
 * @param registry The registry to register the resource with.
 * @param opts The resource options.
 * @param fn The resource function.
 * @returns The resource action.
 */
export function defineResource(
  registry: Registry,
  opts: ResourceOptions,
  fn: ResourceFn
): ResourceAction {
  const uri = opts.uri ?? opts.template;
  if (!uri) {
    throw new GenkitError({
      status: 'INVALID_ARGUMENT',
      message: `must specify either url or template options`,
    });
  }
  const template = opts.template ? uriTemplate(opts.template) : undefined;
  const matcher = opts.uri
    ? (input: string) => (input === opts.uri ? {} : undefined)
    : (input: string) => {
        return template!.fromUri(input);
      };

  const action = defineAction(
    registry,
    {
      actionType: 'resource',
      name: uri,
      description: opts.description,
      inputSchema: z.string(),
      outputSchema: z.array(PartSchema),
      metadata: {
        resource: {
          uri: opts.uri,
          template: opts.template,
        },
      },
    },
    async (input, ctx) => {
      const templateMatch = matcher(input);
      if (!templateMatch) {
        throw new GenkitError({
          status: 'INVALID_ARGUMENT',
          message: `input ${input} did not match template ${uri}`,
        });
      }
      return await fn(templateMatch, ctx);
    }
  ) as ResourceAction;

  action.matches = (input: string) => matcher(input) !== undefined;

  return action;
}

/**
 * Finds a matching resource in the registry. If not found returns undefined.
 */
export async function findMatchingResource(
  registry: Registry,
  input: string
): Promise<ResourceAction | undefined> {
  for (const actKeys of Object.keys(await registry.listResolvableActions())) {
    if (actKeys.startsWith('/resource/')) {
      const resource = (await registry.lookupAction(actKeys)) as ResourceAction;
      if (resource.matches(input)) {
        return resource;
      }
    }
  }
  return undefined;
}
