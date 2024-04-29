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

import { describe, expect, it, jest } from '@jest/globals';
import * as configModule from '../../src/plugin/config';
import { TraceData } from '../../src/types/trace';
import { getEvalExtractors } from '../../src/utils/eval';

const CONTEXT_TEXTS = [
  'are about 10 times larger, making them particularly difficultfor humans to ignore.',
  'they are very big animals',
];
const MOCK_TRACE: TraceData = {
  traceId: '7c273c22b219d077c6731a10d46b7d40',
  displayName: 'dev-run-action-wrapper',
  startTime: 1714059149480,
  endTime: 1714059149486.6926,
  spans: {
    dfe3b782071ea308: {
      spanId: 'dfe3b782071ea308',
      traceId: '7c273c22b219d077c6731a10d46b7d40',
      parentSpanId: '30506fdf0beccc15',
      startTime: 1714059149481,
      endTime: 1714059149481.1533,
      attributes: {
        'genkit:type': 'flowStep',
        'genkit:name': 'step1',
        'genkit:path': '/dev-run-action-wrapper/multiSteps/multiSteps/step1',
        'genkit:metadata:flow:stepType': 'run',
        'genkit:metadata:flow:stepName': 'step1',
        'genkit:metadata:flow:resolvedStepName': 'step1',
        'genkit:metadata:flow:state': 'run',
        'genkit:output': '"Hello, Douglas Adams! step 1"',
        'genkit:state': 'success',
      },
      displayName: 'step1',
      links: [],
      instrumentationLibrary: {
        name: 'genkit-tracer',
        version: 'v1',
      },
      spanKind: 'INTERNAL',
      sameProcessAsParentSpan: {
        value: true,
      },
      status: {
        code: 0,
      },
      timeEvents: {
        timeEvent: [],
      },
    },
    dd735a0ba4e4dafd: {
      spanId: 'dd735a0ba4e4dafd',
      traceId: '7c273c22b219d077c6731a10d46b7d40',
      parentSpanId: '30506fdf0beccc15',
      startTime: 1714059149481,
      endTime: 1714059149481.3718,
      attributes: {
        'genkit:type': 'flowStep',
        'genkit:name': 'step2',
        'genkit:path': '/dev-run-action-wrapper/multiSteps/multiSteps/step2',
        'genkit:metadata:flow:stepType': 'run',
        'genkit:metadata:flow:stepName': 'step2',
        'genkit:metadata:flow:resolvedStepName': 'step2',
        'genkit:metadata:flow:state': 'run',
        'genkit:input': '"Hello, Douglas Adams! step 1"',
        'genkit:output': '"Hello, Douglas Adams! step 1 Faf "',
        'genkit:state': 'success',
      },
      displayName: 'step2',
      links: [],
      instrumentationLibrary: {
        name: 'genkit-tracer',
        version: 'v1',
      },
      spanKind: 'INTERNAL',
      sameProcessAsParentSpan: {
        value: true,
      },
      status: {
        code: 0,
      },
      timeEvents: {
        timeEvent: [],
      },
    },
    b002dd6a0d92977d: {
      spanId: 'b002dd6a0d92977d',
      traceId: '7c273c22b219d077c6731a10d46b7d40',
      parentSpanId: '30506fdf0beccc15',
      startTime: 1714097043891,
      endTime: 1714097044574.1538,
      attributes: {
        'genkit:type': 'action',
        'genkit:name': 'devLocalVectorstore/pdfQA',
        'genkit:path':
          '/dev-run-action-wrapper/multiSteps/multiSteps/devLocalVectorstore/pdfQA',
        'genkit:input':
          '{"query":{"content":[{"text":"What are cats?"}]},"options":{"k":3}}',
        'genkit:metadata:subtype': 'retriever',
        'genkit:output':
          '{"documents":[{"content":[{"text":"are about 10 times larger, making them particularly difficultfor humans to ignore."}]},{"content":[{"text":"they are very big animals"}]}]}',
        'genkit:state': 'success',
      },
      displayName: 'devLocalVectorstore/pdfQA',
      links: [],
      instrumentationLibrary: {
        name: 'genkit-tracer',
        version: 'v1',
      },
      spanKind: 'INTERNAL',
      sameProcessAsParentSpan: {
        value: true,
      },
      status: {
        code: 0,
      },
      timeEvents: {
        timeEvent: [],
      },
    },
    '41b5ce70e453ae02': {
      spanId: '41b5ce70e453ae02',
      traceId: '7c273c22b219d077c6731a10d46b7d40',
      parentSpanId: '30506fdf0beccc15',
      startTime: 1714059149482,
      endTime: 1714059149482.3955,
      attributes: {
        'genkit:type': 'flowStep',
        'genkit:name': 'step3-array',
        'genkit:path':
          '/dev-run-action-wrapper/multiSteps/multiSteps/step3-array',
        'genkit:metadata:flow:stepType': 'run',
        'genkit:metadata:flow:stepName': 'step3-array',
        'genkit:metadata:flow:resolvedStepName': 'step3-array',
        'genkit:metadata:flow:state': 'run',
        'genkit:output':
          '["Hello, Douglas Adams! step 1 Faf ","Hello, Douglas Adams! step 1 Faf "]',
        'genkit:state': 'success',
      },
      displayName: 'step3-array',
      links: [],
      instrumentationLibrary: {
        name: 'genkit-tracer',
        version: 'v1',
      },
      spanKind: 'INTERNAL',
      sameProcessAsParentSpan: {
        value: true,
      },
      status: {
        code: 0,
      },
      timeEvents: {
        timeEvent: [],
      },
    },
    '39e81338f055c25b': {
      spanId: '39e81338f055c25b',
      traceId: '7c273c22b219d077c6731a10d46b7d40',
      parentSpanId: '30506fdf0beccc15',
      startTime: 1714059149483,
      endTime: 1714059149483.3872,
      attributes: {
        'genkit:type': 'flowStep',
        'genkit:name': 'step4-num',
        'genkit:path':
          '/dev-run-action-wrapper/multiSteps/multiSteps/step4-num',
        'genkit:metadata:flow:stepType': 'run',
        'genkit:metadata:flow:stepName': 'step4-num',
        'genkit:metadata:flow:resolvedStepName': 'step4-num',
        'genkit:metadata:flow:state': 'run',
        'genkit:output':
          '"Hello, Douglas Adams! step 1 Faf -()-Hello, Douglas Adams! step 1 Faf "',
        'genkit:state': 'success',
      },
      displayName: 'step4-num',
      links: [],
      instrumentationLibrary: {
        name: 'genkit-tracer',
        version: 'v1',
      },
      spanKind: 'INTERNAL',
      sameProcessAsParentSpan: {
        value: true,
      },
      status: {
        code: 0,
      },
      timeEvents: {
        timeEvent: [],
      },
    },
    '30506fdf0beccc15': {
      spanId: '30506fdf0beccc15',
      traceId: '7c273c22b219d077c6731a10d46b7d40',
      parentSpanId: 'eec307f9311c5617',
      startTime: 1714059149481,
      endTime: 1714059149484.9653,
      attributes: {
        'genkit:type': 'flow',
        'genkit:name': 'multiSteps',
        'genkit:isRoot': true,
        'genkit:path': '/dev-run-action-wrapper/multiSteps/multiSteps',
        'genkit:metadata:flow:execution': '0',
        'genkit:metadata:flow:name': 'multiSteps',
        'genkit:metadata:flow:id': 'c68dd3b2-6bb4-44ef-907d-cef5720d6b6b',
        'genkit:metadata:flow:dispatchType': 'start',
        'genkit:metadata:flow:state': 'done',
        'genkit:input': '"Douglas Adams"',
        'genkit:output': '42',
        'genkit:state': 'success',
      },
      displayName: 'multiSteps',
      links: [],
      instrumentationLibrary: {
        name: 'genkit-tracer',
        version: 'v1',
      },
      spanKind: 'INTERNAL',
      sameProcessAsParentSpan: {
        value: true,
      },
      status: {
        code: 0,
      },
      timeEvents: {
        timeEvent: [],
      },
    },
    eec307f9311c5617: {
      spanId: 'eec307f9311c5617',
      traceId: '7c273c22b219d077c6731a10d46b7d40',
      parentSpanId: '98e7d0c2f5e90f4e',
      startTime: 1714059149480,
      endTime: 1714059149485.578,
      attributes: {
        'genkit:type': 'action',
        'genkit:name': 'multiSteps',
        'genkit:path': '/dev-run-action-wrapper/multiSteps',
        'genkit:input': '{"start":{"input":"Douglas Adams"}}',
        'genkit:metadata:flow:wrapperAction': 'true',
        'genkit:output':
          '{"flowId":"c68dd3b2-6bb4-44ef-907d-cef5720d6b6b","name":"multiSteps","startTime":1714059149480,"input":"Douglas Adams","cache":{"step1":{"value":"Hello, Douglas Adams! step 1"},"step2":{"value":"Hello, Douglas Adams! step 1 Faf "},"step3-array":{"value":["Hello, Douglas Adams! step 1 Faf ","Hello, Douglas Adams! step 1 Faf "]},"step4-num":{"value":"Hello, Douglas Adams! step 1 Faf -()-Hello, Douglas Adams! step 1 Faf "}},"eventsTriggered":{},"blockedOnStep":null,"executions":[{"startTime":1714059149481,"traceIds":["7c273c22b219d077c6731a10d46b7d40"]}],"operation":{"name":"c68dd3b2-6bb4-44ef-907d-cef5720d6b6b","done":true,"result":{"response":42}},"traceContext":"{\\"traceId\\":\\"7c273c22b219d077c6731a10d46b7d40\\",\\"spanId\\":\\"30506fdf0beccc15\\",\\"traceFlags\\":1}"}',
        'genkit:state': 'success',
      },
      displayName: 'multiSteps',
      links: [],
      instrumentationLibrary: {
        name: 'genkit-tracer',
        version: 'v1',
      },
      spanKind: 'INTERNAL',
      sameProcessAsParentSpan: {
        value: true,
      },
      status: {
        code: 0,
      },
      timeEvents: {
        timeEvent: [],
      },
    },
    '98e7d0c2f5e90f4e': {
      spanId: '98e7d0c2f5e90f4e',
      traceId: '7c273c22b219d077c6731a10d46b7d40',
      startTime: 1714059149480,
      endTime: 1714059149486.6926,
      attributes: {
        'genkit:name': 'dev-run-action-wrapper',
        'genkit:isRoot': true,
        'genkit:path': '/dev-run-action-wrapper',
        'genkit:metadata:genkit-dev-internal': 'true',
        'genkit:state': 'success',
      },
      displayName: 'dev-run-action-wrapper',
      links: [],
      instrumentationLibrary: {
        name: 'genkit-tracer',
        version: 'v1',
      },
      spanKind: 'INTERNAL',
      sameProcessAsParentSpan: {
        value: true,
      },
      status: {
        code: 0,
      },
      timeEvents: {
        timeEvent: [],
      },
    },
  },
};

describe('eval utils', () => {
  it('returns default extractors when no config provided', async () => {
    const spy = jest.spyOn(configModule, 'findToolsConfig');
    spy.mockReturnValue(Promise.resolve(null));

    const extractors = await getEvalExtractors('multiSteps');

    expect(Object.keys(extractors).sort()).toEqual(
      ['input', 'output', 'context'].sort()
    );
    expect(extractors.input(MOCK_TRACE)).toEqual(
      JSON.stringify('Douglas Adams')
    );
    expect(extractors.output(MOCK_TRACE)).toEqual(JSON.stringify(42));
    expect(extractors.context(MOCK_TRACE)).toEqual(
      JSON.stringify(CONTEXT_TEXTS)
    );
  });

  it('returns custom extractors by stepName', async () => {
    const config: configModule.ToolsConfig = {
      evaluators: [
        {
          flowName: 'multiSteps',
          extractors: {
            output: 'step1',
          },
        },
      ],
    };
    const spy = jest.spyOn(configModule, 'findToolsConfig');
    spy.mockReturnValue(Promise.resolve(config));

    const extractors = await getEvalExtractors('multiSteps');

    expect(extractors.input(MOCK_TRACE)).toEqual(
      JSON.stringify('Douglas Adams')
    );
    expect(extractors.output(MOCK_TRACE)).toEqual(
      JSON.stringify('Hello, Douglas Adams! step 1')
    );
    expect(extractors.context(MOCK_TRACE)).toEqual(
      JSON.stringify(CONTEXT_TEXTS)
    );
  });

  it('returns custom extractors by stepSelector', async () => {
    const config: configModule.ToolsConfig = {
      evaluators: [
        {
          flowName: 'multiSteps',
          extractors: {
            output: { inputOf: 'step2' },
            context: { outputOf: 'step3-array' },
          },
        },
      ],
    };
    const spy = jest.spyOn(configModule, 'findToolsConfig');
    spy.mockReturnValue(Promise.resolve(config));

    const extractors = await getEvalExtractors('multiSteps');

    expect(extractors.input(MOCK_TRACE)).toEqual(
      JSON.stringify('Douglas Adams')
    );
    expect(extractors.output(MOCK_TRACE)).toEqual(
      JSON.stringify('Hello, Douglas Adams! step 1')
    );
    expect(extractors.context(MOCK_TRACE)).toEqual(
      JSON.stringify([
        'Hello, Douglas Adams! step 1 Faf ',
        'Hello, Douglas Adams! step 1 Faf ',
      ])
    );
  });

  it('returns custom extractors by trace function', async () => {
    const config: configModule.ToolsConfig = {
      evaluators: [
        {
          flowName: 'multiSteps',
          extractors: {
            input: (trace: TraceData) => {
              return JSON.stringify(
                Object.values(trace.spans)
                  .filter(
                    (s) =>
                      s.attributes['genkit:type'] === 'action' &&
                      s.attributes['genkit:metadata:subtype'] !== 'retriever'
                  )
                  .map((s) => {
                    const inputValue = JSON.parse(
                      s.attributes['genkit:input'] as string
                    ).start.input;
                    if (!inputValue) {
                      return '';
                    }
                    return inputValue + ' TEST TEST TEST';
                  })
              );
            },
            output: { inputOf: 'step2' },
            context: { outputOf: 'step3-array' },
          },
        },
      ],
    };
    const spy = jest.spyOn(configModule, 'findToolsConfig');
    spy.mockReturnValue(Promise.resolve(config));

    const extractors = await getEvalExtractors('multiSteps');

    expect(extractors.input(MOCK_TRACE)).toEqual(
      JSON.stringify(['Douglas Adams TEST TEST TEST'])
    );
    expect(extractors.output(MOCK_TRACE)).toEqual(
      JSON.stringify('Hello, Douglas Adams! step 1')
    );
    expect(extractors.context(MOCK_TRACE)).toEqual(
      JSON.stringify([
        'Hello, Douglas Adams! step 1 Faf ',
        'Hello, Douglas Adams! step 1 Faf ',
      ])
    );
  });
});
