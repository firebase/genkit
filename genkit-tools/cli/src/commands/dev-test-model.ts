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

import {
  GenerateRequestData,
  GenerateResponseData,
} from '@genkit-ai/tools-common';
import {
  GenkitToolsError,
  RuntimeManager,
} from '@genkit-ai/tools-common/manager';
import { findProjectRoot, logger } from '@genkit-ai/tools-common/utils';
import { Command } from 'commander';
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { parse } from 'yaml';
import { startDevProcessManager, startManager } from '../utils/manager-utils';

interface TestOptions {
  supports: string;
  fromFile?: string;
}

type TestCase = {
  name: string;
  input: GenerateRequestData;
  validators: string[];
};

type TestSuite = {
  model: string;
  supports?: string[];
  tests?: TestCase[];
};

const getMessageText = (response: GenerateResponseData): string | undefined => {
  const message = response.message || response.candidates?.[0]?.message;
  return message?.content?.[0]?.text;
};

const getMessageContent = (response: GenerateResponseData) => {
  const message = response.message || response.candidates?.[0]?.message;
  return message?.content;
};

const getMediaPart = (response: GenerateResponseData) => {
  const content = getMessageContent(response);
  return content?.find((p: any) => p.media);
};

const VALIDATORS: Record<
  string,
  (response: GenerateResponseData, arg?: string) => void
> = {
  'has-tool-request': (response, toolName) => {
    const content = getMessageContent(response);
    if (!content || !Array.isArray(content)) {
      throw new Error(
        `Response missing message content. Full response: ${JSON.stringify(
          response,
          null,
          2
        )}`
      );
    }
    const toolRequest = content.find((c: any) => c.toolRequest);
    if (!toolRequest) {
      throw new Error(
        `Model did not return a tool request. Content: ${JSON.stringify(
          content,
          null,
          2
        )}`
      );
    }
    if (toolName && toolRequest.toolRequest?.name !== toolName) {
      throw new Error(
        `Expected tool request '${toolName}', got '${toolRequest.toolRequest?.name}'`
      );
    }
  },
  'valid-json': (response) => {
    const content = getMessageContent(response);
    if (!content || !Array.isArray(content)) {
      throw new Error(
        `Response missing message content. Full response: ${JSON.stringify(
          response,
          null,
          2
        )}`
      );
    }
    const textPart = content.find((c: any) => c.text);
    if (!textPart) {
      throw new Error(
        `Model did not return text content for JSON. Content: ${JSON.stringify(
          content,
          null,
          2
        )}`
      );
    }
    try {
      JSON.parse(textPart.text!);
    } catch (e) {
      throw new Error(
        `Response text is not valid JSON. Text: ${textPart.text}`
      );
    }
  },
  'text-includes': (response, expected) => {
    const text = getMessageText(response);
    if (
      !text ||
      (expected && !text.toLowerCase().includes(expected.toLowerCase()))
    ) {
      throw new Error(
        `Response text does not include '${expected}'. Text: ${text}`
      );
    }
  },
  'text-starts-with': (response, expected) => {
    const text = getMessageText(response);
    if (!text || (expected && !text.trim().startsWith(expected))) {
      throw new Error(
        `Response text does not start with '${expected}'. Text: ${text}`
      );
    }
  },
  'text-not-empty': (response) => {
    const text = getMessageText(response);
    if (!text || text.trim().length === 0) {
      throw new Error('Response text is empty');
    }
  },
  'valid-media': (response, type) => {
    const mediaPart = getMediaPart(response);
    if (!mediaPart) {
      throw new Error(`Model did not return ${type || 'media'} part.`);
    }
    if (type) {
      if (
        mediaPart.media?.contentType &&
        !mediaPart.media.contentType.startsWith(`${type}/`)
      ) {
        throw new Error(
          `Expected ${type} content type, got ${mediaPart.media.contentType}`
        );
      }
    }
    if (type === 'image') {
      const url = mediaPart.media?.url;
      if (!url) throw new Error('Media part missing URL');
      if (url.startsWith('data:')) {
        if (!url.startsWith('data:image/')) {
          throw new Error('Invalid data URL content type for image');
        }
      } else if (url.startsWith('http')) {
        try {
          new URL(url);
        } catch (e) {
          throw new Error(`Invalid URL: ${url}`);
        }
      } else {
        throw new Error(`Unknown URL format: ${url}`);
      }
    }
  },
};

const TEST_CASES: Record<string, TestCase> = {
  'tool-request': {
    name: 'Tool Request Conformance',
    input: {
      messages: [
        {
          role: 'user',
          content: [{ text: 'What is the weather in New York? Use the tool.' }],
        },
      ],
      tools: [
        {
          name: 'weather',
          description: 'Get the weather for a city',
          inputSchema: {
            type: 'object',
            properties: {
              city: { type: 'string' },
            },
            required: ['city'],
          },
        },
      ],
    },
    validators: ['has-tool-request:weather'],
  },
  'structured-output': {
    name: 'Structured Output Conformance',
    input: {
      messages: [
        {
          role: 'user',
          content: [{ text: 'Generate a profile for John Doe.' }],
        },
      ],
      output: {
        format: 'json',
        schema: {
          type: 'object',
          properties: {
            name: { type: 'string' },
            age: { type: 'number' },
          },
          required: ['name', 'age'],
        },
      },
    },
    validators: ['valid-json'],
  },
  multiturn: {
    name: 'Multiturn Conformance',
    input: {
      messages: [
        { role: 'user', content: [{ text: 'My name is Genkit.' }] },
        { role: 'model', content: [{ text: 'Hello Genkit.' }] },
        { role: 'user', content: [{ text: 'What is my name?' }] },
      ],
    },
    validators: ['text-includes:Genkit'],
  },
  context: {
    name: 'Context Conformance',
    input: {
      messages: [
        { role: 'user', content: [{ text: 'What is the secret code?' }] },
      ],
      docs: [{ content: [{ text: 'The secret code is 42.' }] }],
    },
    validators: ['text-includes:42'],
  },
  'system-role': {
    name: 'System Role Conformance',
    input: {
      messages: [
        {
          role: 'system',
          content: [
            {
              text: "IMPORTANT: your response are machine processed, always start/prefix your response with 'RESPONSE:', ex: 'RESPONSE: hello'",
            },
          ],
        },
        { role: 'user', content: [{ text: 'hello' }] },
      ],
    },
    validators: ['text-starts-with:RESPONSE:'],
  },
  'input-image-base64': {
    name: 'Image Input (Base64) Conformance',
    input: {
      messages: [
        {
          role: 'user',
          content: [
            { text: 'What color is this?' },
            {
              media: {
                url: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
                contentType: 'image/png',
              },
            },
          ],
        },
      ],
    },
    validators: ['text-includes:red'],
  },
  'input-image-url': {
    name: 'Image Input (URL) Conformance',
    input: {
      messages: [
        {
          role: 'user',
          content: [
            { text: 'What is this logo?' },
            {
              media: {
                url: 'https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png',
                contentType: 'image/png',
              },
            },
          ],
        },
      ],
    },
    validators: ['text-includes:google'],
  },
  'input-video-youtube': {
    name: 'Video Input (YouTube) Conformance',
    input: {
      messages: [
        {
          role: 'user',
          content: [
            { text: 'Describe this video.' },
            {
              media: {
                url: 'https://www.youtube.com/watch?v=3p1P5grjXIQ',
                contentType: 'video/mp4',
              },
            },
          ],
        },
      ],
    },
    validators: ['text-not-empty'],
  },
  'output-audio': {
    name: 'Audio Output (TTS) Conformance',
    input: {
      messages: [{ role: 'user', content: [{ text: 'Say hello.' }] }],
    },
    validators: ['valid-media:audio'],
  },
  'output-image': {
    name: 'Image Output (Generation) Conformance',
    input: {
      messages: [
        {
          role: 'user',
          content: [{ text: 'Generate an image of a cat.' }],
        },
      ],
    },
    validators: ['valid-media:image'],
  },
};

async function waitForRuntime(manager: RuntimeManager) {
  // Poll for runtimes
  for (let i = 0; i < 20; i++) {
    if (manager.listRuntimes().length > 0) return;
    await new Promise((r) => setTimeout(r, 500));
  }
  logger.warn('Runtime not detected after 10 seconds.');
}

async function runTest(
  manager: RuntimeManager,
  model: string,
  testCase: TestCase
): Promise<boolean> {
  logger.info(`Running test: ${testCase.name}...`);
  try {
    // Adjust model name if needed (e.g. /model/ prefix)
    const modelKey = model.startsWith('/') ? model : `/model/${model}`;
    const actionResponse = await manager.runAction({
      key: modelKey,
      input: testCase.input,
    });

    const response = actionResponse.result as GenerateResponseData;

    for (const v of testCase.validators) {
      const [valName, ...args] = v.split(':');
      const arg = args.join(':');
      const validator = VALIDATORS[valName];
      if (!validator) throw new Error(`Unknown validator: ${valName}`);
      validator(response, arg);
    }

    logger.info(`✅ Passed: ${testCase.name}`);
    return true;
  } catch (e) {
    if (e instanceof GenkitToolsError) {
      logger.error(
        `❌ Failed: ${testCase.name} - ${
          e.data?.stack || JSON.stringify(e.data?.details) || e
        }`
      );
    } else if (e instanceof Error) {
      logger.error(`❌ Failed: ${testCase.name} - ${e.message}`);
    } else {
      logger.error(`❌ Failed: ${testCase.name} - ${JSON.stringify(e)}`);
    }
    return false;
  }
}

async function runTestSuite(
  manager: RuntimeManager,
  suite: TestSuite,
  defaultSupports: string[]
): Promise<{ passed: number; failed: number }> {
  const supports = suite.supports || (suite.tests ? [] : defaultSupports);

  logger.info(`Testing model: ${suite.model}`);

  const promises: Promise<boolean>[] = [];

  // Built-in conformance tests
  for (const support of supports) {
    const testCase = TEST_CASES[support];
    if (testCase) {
      promises.push(runTest(manager, suite.model, testCase));
    } else {
      logger.warn(`Unknown capability: ${support}`);
    }
  }

  // Custom tests
  if (suite.tests) {
    for (const test of suite.tests) {
      const customTestCase: TestCase = {
        name: test.name || 'Custom Test',
        input: test.input,
        validators: test.validators || [],
      };
      promises.push(runTest(manager, suite.model, customTestCase));
    }
  }

  const results = await Promise.all(promises);
  const passed = results.filter((r) => r).length;
  const failed = results.filter((r) => !r).length;

  return { passed, failed };
}

export const devTestModel = new Command('dev-test-model')
  .description('Test a model against the Genkit model specification')
  .argument('[modelOrCmd]', 'Model name or command')
  .argument('[args...]', 'Command arguments')
  .option(
    '--supports <list>',
    'Comma-separated list of supported capabilities (tool-request, structured-output, multiturn, context, system-role, input-image-base64, input-image-url, input-video-youtube, output-audio, output-image)',
    'tool-request,structured-output,multiturn,context,system-role,input-image-base64,input-image-url,input-video-youtube'
  )
  .option('--from-file <file>', 'Path to a file containing test payloads')
  .action(
    async (
      modelOrCmd: string | undefined,
      args: string[] | undefined,
      options: TestOptions
    ) => {
      const projectRoot = await findProjectRoot();

      let cmd: string[] = [];
      let defaultModelName: string | undefined;

      if (options.fromFile) {
        if (modelOrCmd) cmd.push(modelOrCmd);
        if (args) cmd.push(...args);
      } else {
        if (!modelOrCmd) {
          logger.error('Model name is required unless --from-file is used.');
          process.exit(1);
        }
        defaultModelName = modelOrCmd;
        if (args) cmd = args;
      }

      let manager: RuntimeManager;

      if (cmd.length > 0) {
        const result = await startDevProcessManager(
          projectRoot,
          cmd[0],
          cmd.slice(1)
        );
        manager = result.manager;
      } else {
        manager = await startManager(projectRoot, false);
      }

      await waitForRuntime(manager);

      try {
        let totalPassed = 0;
        let totalFailed = 0;

        let suites: TestSuite[] = [];

        if (options.fromFile) {
          const filePath = resolve(projectRoot, options.fromFile);
          const fileContent = readFileSync(filePath, 'utf-8');
          let parsed;
          if (filePath.endsWith('.yaml') || filePath.endsWith('.yml')) {
            parsed = parse(fileContent);
          } else {
            parsed = JSON.parse(fileContent);
          }
          suites = Array.isArray(parsed) ? parsed : [parsed];
        } else {
          if (!defaultModelName) throw new Error('Model name required');
          suites = [{ model: defaultModelName }];
        }

        const defaultSupports = options.supports
          .split(',')
          .map((s) => s.trim());

        for (const suite of suites) {
          if (!suite.model) {
            logger.error('Model name required in test suite.');
            totalFailed++;
            continue;
          }
          const { passed, failed } = await runTestSuite(
            manager,
            suite,
            defaultSupports
          );
          totalPassed += passed;
          totalFailed += failed;
        }

        logger.info('--------------------------------------------------');
        logger.info(
          `Tests Completed: ${totalPassed} Passed, ${totalFailed} Failed`
        );

        if (totalFailed > 0) {
          process.exit(1);
        } else {
          process.exit(0);
        }
      } catch (e) {
        logger.error('Error running tests:', e);
        process.exit(1);
      }
    }
  );
