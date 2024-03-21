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
  internalMetricNamespaceWrap,
  MetricCounter,
  MetricHistogram,
} from '@genkit-ai/common/metrics';
import { ValueType } from '@opentelemetry/api';

/**
 * Wraps the declared metrics in a Genkit-specific, internal namespace.
 */
const _N = internalMetricNamespaceWrap.bind(null, 'ai');

const generateActionCounter = new MetricCounter(_N('generate_requests'), {
  description: 'Counts calls to genkit generate actions.',
  valueType: ValueType.INT,
});

const generateActionLatencies = new MetricHistogram(_N('generate_latency'), {
  description: 'Latencies when interacting with a Genkit model.',
  valueType: ValueType.INT,
  unit: 'ms',
});

const generateActionInputCharacters = new MetricHistogram(
  _N('generate_input_characters'),
  {
    description: 'Histogram of input characters to a Genkit model.',
    valueType: ValueType.INT,
  }
);

const generateActionInputTokens = new MetricHistogram(
  _N('generate_input_tokens'),
  {
    description: 'Histogram of input tokens to a Genkit model.',
    valueType: ValueType.INT,
  }
);

const generateActionInputImages = new MetricHistogram(
  _N('generate_input_images'),
  {
    description: 'Histogram of input images to a Genkit model.',
    valueType: ValueType.INT,
  }
);

const generateActionOutputCharacters = new MetricHistogram(
  _N('generate_output_characters'),
  {
    description: 'Histogram of output characters to a Genkit model.',
    valueType: ValueType.INT,
  }
);

const generateActionOutputTokens = new MetricHistogram(
  _N('generate_output_tokens'),
  {
    description: 'Histogram of output tokens to a Genkit model.',
    valueType: ValueType.INT,
  }
);

const generateActionOutputImages = new MetricHistogram(
  _N('generate_output_images'),
  {
    description: 'Histogram of output images to a Genkit model.',
    valueType: ValueType.INT,
  }
);

type SharedDimensions = {
  modelName?: string;
  path?: string;
  temperature?: number;
  topK?: number;
  topP?: number;
};

/**
 * Records all metrics associated with performing a GenerateAction.
 */
export function recordGenerateAction(
  modelName: string,
  dimensions: {
    path?: string;
    temperature?: number;
    maxOutputTokens?: number;
    topK?: number;
    topP?: number;
    inputTokens?: number;
    outputTokens?: number;
    totalTokens?: number;
    inputCharacters?: number;
    outputCharacters?: number;
    totalCharacters?: number;
    inputImages?: number;
    outputImages?: number;
    latencyMs?: number;
    err?: any;
  }
) {
  const shared: SharedDimensions = {
    modelName: modelName,
    path: dimensions.path,
    temperature: dimensions.temperature,
    topK: dimensions.topK,
    topP: dimensions.topP,
  };

  generateActionCounter.add(1, {
    maxOutputTokens: dimensions.maxOutputTokens,
    errorCode: dimensions.err?.code,
    errorMessage: dimensions.err?.message,
    ...shared,
  });

  generateActionLatencies.record(dimensions.latencyMs, shared);

  // inputs
  generateActionInputTokens.record(dimensions.inputTokens, shared);
  generateActionInputCharacters.record(dimensions.inputCharacters, shared);
  generateActionInputImages.record(dimensions.inputImages, shared);

  // outputs
  generateActionOutputTokens.record(dimensions.outputTokens, shared);
  generateActionOutputCharacters.record(dimensions.outputCharacters, shared);
  generateActionOutputImages.record(dimensions.outputImages, shared);
}
