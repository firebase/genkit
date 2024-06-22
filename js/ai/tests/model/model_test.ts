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

import { __hardResetRegistryForTesting } from '@genkit-ai/core/registry';
import assert from 'node:assert';
import { beforeEach, describe, it } from 'node:test';
import { generate } from '../../src/generate.js';
import {
  ModelAction,
  ModelMiddleware,
  defineModel,
  defineWrappedModel,
} from '../../src/model.js';

const wrapRequest: ModelMiddleware = async (req, next) => {
  return next({
    ...req,
    messages: [
      {
        role: 'user',
        content: [
          {
            text:
              '(' +
              req.messages
                .map((m) => m.content.map((c) => c.text).join())
                .join() +
              ')',
          },
        ],
      },
    ],
  });
};
const wrapResponse: ModelMiddleware = async (req, next) => {
  const res = await next(req);
  return {
    candidates: [
      {
        index: 0,
        finishReason: 'stop',
        message: {
          role: 'model',
          content: [
            {
              text:
                '[' +
                res.candidates[0].message.content.map((c) => c.text).join() +
                ']',
            },
          ],
        },
      },
    ],
  };
};

describe('defineWrappedModel', () => {
  beforeEach(__hardResetRegistryForTesting);

  var echoModel: ModelAction;
  var wrappedEchoModel: ModelAction;

  beforeEach(() => {
    echoModel = defineModel(
      {
        name: 'echoModel',
        label: 'echo-echo-echo-echo-echo',
        supports: {
          multiturn: true,
        },
      },
      async (request) => {
        return {
          candidates: [
            {
              index: 0,
              finishReason: 'stop',
              message: {
                role: 'model',
                content: [
                  {
                    text:
                      'Echo: ' +
                      request.messages
                        .map((m) => m.content.map((c) => c.text).join())
                        .join(),
                  },
                ],
              },
            },
          ],
        };
      }
    );
    wrappedEchoModel = defineWrappedModel({
      name: 'wrappedModel',
      model: echoModel,
      info: {
        label: 'Wrapped Echo',
      },
      use: [wrapRequest, wrapResponse],
    });
  });

  it('copies/overwrites metadata', async () => {
    assert.deepStrictEqual(wrappedEchoModel.__action.metadata, {
      model: {
        label: 'Wrapped Echo',
        customOptions: undefined,
        versions: undefined,
        supports: {
          multiturn: true,
        },
      },
    });
  });

  it('applies middleware', async () => {
    const response = await generate({
      prompt: 'banana',
      model: wrappedEchoModel,
    });

    const want = '[Echo: (banana)]';
    assert.deepStrictEqual(response.text(), want);
  });
});
