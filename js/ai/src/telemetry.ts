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

import { GENKIT_VERSION } from '@genkit-ai/core';
import { logger } from '@genkit-ai/core/logging';
import {
  internalMetricNamespaceWrap,
  MetricCounter,
  MetricHistogram,
} from '@genkit-ai/core/metrics';
import { spanMetadataAls } from '@genkit-ai/core/tracing';
import { ValueType } from '@opentelemetry/api';
import { createHash } from 'crypto';
import { GenerateOptions } from './generate.js';
import {
  GenerateRequest,
  GenerateResponseData,
  GenerationUsage,
  MediaPart,
  Part,
  ToolRequestPart,
  ToolResponsePart,
} from './model.js';

/** The maximum length (in characters) of a logged prompt message. */
const MAX_LOG_CONTENT_CHARS = 128_000;

/**
 * Wraps the declared metrics in a Genkit-specific, internal namespace.
 */
const _N = internalMetricNamespaceWrap.bind(null, 'ai');

const generateActionCounter = new MetricCounter(_N('generate/requests'), {
  description: 'Counts calls to genkit generate actions.',
  valueType: ValueType.INT,
});

const generateActionLatencies = new MetricHistogram(_N('generate/latency'), {
  description: 'Latencies when interacting with a Genkit model.',
  valueType: ValueType.DOUBLE,
  unit: 'ms',
});

const generateActionInputCharacters = new MetricCounter(
  _N('generate/input/characters'),
  {
    description: 'Counts input characters to any Genkit model.',
    valueType: ValueType.INT,
  }
);

const generateActionInputTokens = new MetricCounter(
  _N('generate/input/tokens'),
  {
    description: 'Counts input tokens to a Genkit model.',
    valueType: ValueType.INT,
  }
);

const generateActionInputImages = new MetricCounter(
  _N('generate/input/images'),
  {
    description: 'Counts input images to a Genkit model.',
    valueType: ValueType.INT,
  }
);

const generateActionInputVideos = new MetricCounter(
  _N('generate/input/videos'),
  {
    description: 'Counts input videos to a Genkit model.',
    valueType: ValueType.INT,
  }
);

const generateActionInputAudio = new MetricCounter(_N('generate/input/audio'), {
  description: 'Counts input audio files to a Genkit model.',
  valueType: ValueType.INT,
});

const generateActionOutputCharacters = new MetricCounter(
  _N('generate/output/characters'),
  {
    description: 'Counts output characters from a Genkit model.',
    valueType: ValueType.INT,
  }
);

const generateActionOutputTokens = new MetricCounter(
  _N('generate/output/tokens'),
  {
    description: 'Counts output tokens from a Genkit model.',
    valueType: ValueType.INT,
  }
);

const generateActionOutputImages = new MetricCounter(
  _N('generate/output/images'),
  {
    description: 'Count output images from a Genkit model.',
    valueType: ValueType.INT,
  }
);

const generateActionOutputVideos = new MetricCounter(
  _N('generate/output/videos'),
  {
    description: 'Count output videos from a Genkit model.',
    valueType: ValueType.INT,
  }
);

const generateActionOutputAudio = new MetricCounter(
  _N('generate/output/audio'),
  {
    description: 'Count output audio files from a Genkit model.',
    valueType: ValueType.INT,
  }
);

type SharedDimensions = {
  modelName?: string;
  path?: string;
  temperature?: number;
  topK?: number;
  topP?: number;
  source?: string;
  sourceVersion?: string;
};

export function recordGenerateActionMetrics(
  modelName: string,
  input: GenerateRequest,
  opts: {
    response?: GenerateResponseData;
    err?: any;
  }
) {
  doRecordGenerateActionMetrics(modelName, opts.response?.usage || {}, {
    temperature: input.config?.temperature,
    topK: input.config?.topK,
    topP: input.config?.topP,
    maxOutputTokens: input.config?.maxOutputTokens,
    path: spanMetadataAls?.getStore()?.path,
    latencyMs: opts.response?.latencyMs,
    err: opts.err,
    source: 'ts',
    sourceVersion: GENKIT_VERSION,
  });
}

export function recordGenerateActionInputLogs(
  model: string,
  options: GenerateOptions,
  input: GenerateRequest
) {
  const path = spanMetadataAls?.getStore()?.path;
  const sharedMetadata = { model, path };
  logger.logStructured(`Config[${path}, ${model}]`, {
    ...sharedMetadata,
    temperature: options.config?.temperature,
    topK: options.config?.topK,
    topP: options.config?.topP,
    maxOutputTokens: options.config?.maxOutputTokens,
    stopSequences: options.config?.stopSequences,
    source: 'ts',
    sourceVersion: GENKIT_VERSION,
  });

  const messages = input.messages.length;
  input.messages.forEach((msg, msgIdx) => {
    const parts = msg.content.length;
    msg.content.forEach((part, partIdx) => {
      const partCounts = toPartCounts(partIdx, parts, msgIdx, messages);
      logger.logStructured(`Input[${path}, ${model}] ${partCounts}`, {
        ...sharedMetadata,
        content: toPartLogContent(part),
        partIndex: partIdx,
        totalParts: parts,
        messageIndex: msgIdx,
        totalMessages: messages,
      });
    });
  });
}

export function recordGenerateActionOutputLogs(
  model: string,
  options: GenerateOptions,
  output: GenerateResponseData
) {
  const path = spanMetadataAls?.getStore()?.path;
  const sharedMetadata = { model, path };
  const candidates = output.candidates.length;
  output.candidates.forEach((cand, candIdx) => {
    const parts = cand.message.content.length;
    cand.message.content.forEach((part, partIdx) => {
      const partCounts = toPartCounts(partIdx, parts, candIdx, candidates);
      const initial = cand.finishMessage
        ? { finishMessage: toPartLogText(cand.finishMessage) }
        : {};
      logger.logStructured(`Output[${path}, ${model}] ${partCounts}`, {
        ...initial,
        ...sharedMetadata,
        content: toPartLogContent(part),
        partIndex: partIdx,
        totalParts: parts,
        candidateIndex: candIdx,
        totalCandidates: candidates,
        messageIndex: cand.index,
        finishReason: cand.finishReason,
      });
    });
  });
}

function toPartCounts(
  partOrdinal: number,
  parts: number,
  msgOrdinal: number,
  messages: number
): string {
  if (parts > 1 && messages > 1) {
    return `(part ${xOfY(partOrdinal, parts)} in message ${xOfY(
      msgOrdinal,
      messages
    )})`;
  }
  if (parts > 1) {
    return `(part ${xOfY(partOrdinal, parts)})`;
  }
  if (messages > 1) {
    return `(message ${xOfY(msgOrdinal, messages)})`;
  }
  return '';
}

function xOfY(x: number, y: number): string {
  return `${x} of ${y}`;
}

function toPartLogContent(part: Part): string {
  if (part.text) {
    return toPartLogText(part.text);
  }
  if (part.media) {
    return toPartLogMedia(part);
  }
  if (part.toolRequest) {
    return toPartLogToolRequest(part);
  }
  if (part.toolResponse) {
    return toPartLogToolResponse(part);
  }
  return '<unknown format>';
}

function toPartLogText(text: string): string {
  return text.substring(0, MAX_LOG_CONTENT_CHARS);
}

function toPartLogMedia(part: MediaPart): string {
  if (part.media.url.startsWith('data:')) {
    const splitIdx = part.media.url.indexOf('base64,');
    if (splitIdx < 0) {
      return '<unknown media format>';
    }
    const prefix = part.media.url.substring(0, splitIdx + 7);
    const hashedContent = createHash('sha256')
      .update(part.media.url.substring(splitIdx + 7))
      .digest('hex');
    return `${prefix}<sha256(${hashedContent})>`;
  }
  return toPartLogText(part.media.url);
}

function toPartLogToolRequest(part: ToolRequestPart): string {
  const inputText =
    typeof part.toolRequest.input === 'string'
      ? part.toolRequest.input
      : JSON.stringify(part.toolRequest.input);
  return toPartLogText(
    `Tool request: ${part.toolRequest.name}, ref: ${part.toolRequest.ref}, input: ${inputText}`
  );
}

function toPartLogToolResponse(part: ToolResponsePart): string {
  const outputText =
    typeof part.toolResponse.output === 'string'
      ? part.toolResponse.output
      : JSON.stringify(part.toolResponse.output);
  return toPartLogText(
    `Tool response: ${part.toolResponse.name}, ref: ${part.toolResponse.ref}, output: ${outputText}`
  );
}

/**
 *
 * Records all metrics associated with performing a GenerateAction.
 */
function doRecordGenerateActionMetrics(
  modelName: string,
  usage: GenerationUsage,
  dimensions: {
    path?: string;
    temperature?: number;
    maxOutputTokens?: number;
    topK?: number;
    topP?: number;
    latencyMs?: number;
    err?: any;
    source?: string;
    sourceVersion: string;
  }
) {
  const shared: SharedDimensions = {
    modelName: modelName,
    path: dimensions.path,
    temperature: dimensions.temperature,
    topK: dimensions.topK,
    topP: dimensions.topP,
    source: dimensions.source,
    sourceVersion: dimensions.sourceVersion,
  };

  generateActionCounter.add(1, {
    maxOutputTokens: dimensions.maxOutputTokens,
    error: dimensions.err?.name,
    ...shared,
  });

  generateActionLatencies.record(dimensions.latencyMs, shared);

  // inputs
  generateActionInputTokens.add(usage.inputTokens, shared);
  generateActionInputCharacters.add(usage.inputCharacters, shared);
  generateActionInputImages.add(usage.inputImages, shared);
  generateActionInputVideos.add(usage.inputVideos, shared);
  generateActionInputAudio.add(usage.inputAudioFiles, shared);

  // outputs
  generateActionOutputTokens.add(usage.outputTokens, shared);
  generateActionOutputCharacters.add(usage.outputCharacters, shared);
  generateActionOutputImages.add(usage.outputImages, shared);
  generateActionOutputVideos.add(usage.outputVideos, shared);
  generateActionOutputAudio.add(usage.outputAudioFiles, shared);
}
