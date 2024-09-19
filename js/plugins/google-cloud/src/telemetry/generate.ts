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
  GenerationUsage,
  MediaPart,
  Part,
  ToolRequestPart,
  ToolResponsePart,
} from '@genkit-ai/ai';
import { GENKIT_VERSION } from '@genkit-ai/core';
import { logger } from '@genkit-ai/core/logging';
import { PathMetadata, toDisplayPath } from '@genkit-ai/core/tracing';
import { ValueType } from '@opentelemetry/api';
import { createHash } from 'crypto';
import {
  MetricCounter,
  MetricHistogram,
  internalMetricNamespaceWrap,
} from '../metrics';

import { ReadableSpan } from '@opentelemetry/sdk-trace-base';
import truncate from 'truncate-utf8-bytes';
import { Telemetry } from '../metrics';
import {
  createCommonLogAttributes,
  extractErrorName,
  extractOuterFlowNameFromPath,
} from '../utils';

type SharedDimensions = {
  modelName?: string;
  flowName?: string;
  path?: string;
  temperature?: number;
  topK?: number;
  topP?: number;
  status?: string;
  source?: string;
  sourceVersion?: string;
};

class GenerateTelemetry implements Telemetry {
  /**
   * Wraps the declared metrics in a Genkit-specific, internal namespace.
   */
  private _N = internalMetricNamespaceWrap.bind(null, 'ai');

  /** The maximum length (in bytes) of a logged prompt message. The maximum log
   * size in GCP is 256kb, so using slightly lower for some buffer for the rest
   * of the message*/
  private MAX_LOG_CONTENT_BYTES = 200_000;

  private actionCounter = new MetricCounter(this._N('generate/requests'), {
    description: 'Counts calls to genkit generate actions.',
    valueType: ValueType.INT,
  });

  private latencies = new MetricHistogram(this._N('generate/latency'), {
    description: 'Latencies when interacting with a Genkit model.',
    valueType: ValueType.DOUBLE,
    unit: 'ms',
  });

  private inputCharacters = new MetricCounter(
    this._N('generate/input/characters'),
    {
      description: 'Counts input characters to any Genkit model.',
      valueType: ValueType.INT,
    }
  );

  private inputTokens = new MetricCounter(this._N('generate/input/tokens'), {
    description: 'Counts input tokens to a Genkit model.',
    valueType: ValueType.INT,
  });

  private inputImages = new MetricCounter(this._N('generate/input/images'), {
    description: 'Counts input images to a Genkit model.',
    valueType: ValueType.INT,
  });

  private inputVideos = new MetricCounter(this._N('generate/input/videos'), {
    description: 'Counts input videos to a Genkit model.',
    valueType: ValueType.INT,
  });

  private inputAudio = new MetricCounter(this._N('generate/input/audio'), {
    description: 'Counts input audio files to a Genkit model.',
    valueType: ValueType.INT,
  });

  private outputCharacters = new MetricCounter(
    this._N('generate/output/characters'),
    {
      description: 'Counts output characters from a Genkit model.',
      valueType: ValueType.INT,
    }
  );

  private outputTokens = new MetricCounter(this._N('generate/output/tokens'), {
    description: 'Counts output tokens from a Genkit model.',
    valueType: ValueType.INT,
  });

  private outputImages = new MetricCounter(this._N('generate/output/images'), {
    description: 'Count output images from a Genkit model.',
    valueType: ValueType.INT,
  });

  private outputVideos = new MetricCounter(this._N('generate/output/videos'), {
    description: 'Count output videos from a Genkit model.',
    valueType: ValueType.INT,
  });

  private outputAudio = new MetricCounter(this._N('generate/output/audio'), {
    description: 'Count output audio files from a Genkit model.',
    valueType: ValueType.INT,
  });

  tick(
    span: ReadableSpan,
    paths: Set<PathMetadata>,
    logIO: boolean,
    projectId?: string
  ): void {
    const attributes = span.attributes;
    const modelName = attributes['genkit:name'] as string;
    const path = (attributes['genkit:path'] as string) || '';
    const input =
      'genkit:input' in attributes
        ? (JSON.parse(
            attributes['genkit:input']! as string
          ) as GenerateRequestData)
        : undefined;
    const output =
      'genkit:output' in attributes
        ? (JSON.parse(
            attributes['genkit:output']! as string
          ) as GenerateResponseData)
        : undefined;

    const errName = extractErrorName(span.events);
    const flowName = extractOuterFlowNameFromPath(path);

    if (input) {
      this.recordGenerateActionMetrics(modelName, flowName, path, input, {
        response: output,
        errName,
      });
      this.recordGenerateActionConfigLogs(
        span,
        modelName,
        flowName,
        path,
        input,
        projectId
      );

      if (logIO) {
        this.recordGenerateActionInputLogs(
          span,
          modelName,
          flowName,
          path,
          input,
          projectId
        );
      }
    }

    if (output && logIO) {
      this.recordGenerateActionOutputLogs(
        span,
        modelName,
        flowName,
        path,
        output,
        projectId
      );
    }
  }

  private recordGenerateActionMetrics(
    modelName: string,
    flowName: string | undefined,
    path: string,
    input: GenerateRequestData,
    opts: {
      response?: GenerateResponseData;
      errName?: string;
    }
  ) {
    this.doRecordGenerateActionMetrics(modelName, opts.response?.usage || {}, {
      temperature: input.config?.temperature,
      topK: input.config?.topK,
      topP: input.config?.topP,
      maxOutputTokens: input.config?.maxOutputTokens,
      flowName,
      path,
      latencyMs: opts.response?.latencyMs,
      errName: opts.errName,
      source: 'ts',
      sourceVersion: GENKIT_VERSION,
    });
  }

  private recordGenerateActionConfigLogs(
    span: ReadableSpan,
    model: string,
    flowName: string | undefined,
    qualifiedPath: string,
    input: GenerateRequestData,
    projectId?: string
  ) {
    const path = toDisplayPath(qualifiedPath);
    const sharedMetadata = {
      ...createCommonLogAttributes(span, projectId),
      model,
      path,
      qualifiedPath,
      flowName,
    };
    logger.logStructured(`Config[${path}, ${model}]`, {
      ...sharedMetadata,
      temperature: input.config?.temperature,
      topK: input.config?.topK,
      topP: input.config?.topP,
      maxOutputTokens: input.config?.maxOutputTokens,
      stopSequences: input.config?.stopSequences,
      source: 'ts',
      sourceVersion: GENKIT_VERSION,
    });
  }

  private recordGenerateActionInputLogs(
    span: ReadableSpan,
    model: string,
    flowName: string | undefined,
    qualifiedPath: string,
    input: GenerateRequestData,
    projectId?: string
  ) {
    const path = toDisplayPath(qualifiedPath);
    const sharedMetadata = {
      ...createCommonLogAttributes(span, projectId),
      model,
      path,
      qualifiedPath,
      flowName,
    };

    const messages = input.messages.length;
    input.messages.forEach((msg, msgIdx) => {
      const parts = msg.content.length;
      msg.content.forEach((part, partIdx) => {
        const partCounts = this.toPartCounts(partIdx, parts, msgIdx, messages);
        logger.logStructured(`Input[${path}, ${model}] ${partCounts}`, {
          ...sharedMetadata,
          content: this.toPartLogContent(part),
          partIndex: partIdx,
          totalParts: parts,
          messageIndex: msgIdx,
          totalMessages: messages,
        });
      });
    });
  }

  private recordGenerateActionOutputLogs(
    span: ReadableSpan,
    model: string,
    flowName: string | undefined,
    qualifiedPath: string,
    output: GenerateResponseData,
    projectId?: string
  ) {
    const path = toDisplayPath(qualifiedPath);
    const sharedMetadata = {
      ...createCommonLogAttributes(span, projectId),
      model,
      path,
      qualifiedPath,
      flowName,
    };
    const candidates = output.candidates.length;

    output.candidates.forEach((cand, candIdx) => {
      const parts = cand.message.content.length;
      const candCounts = parts > 1 ? ` (${candIdx + 1} of ${parts})` : '';
      logger.logStructured(`Output Candidate[${path}, ${model}]${candCounts}`, {
        ...sharedMetadata,
        candidateIndex: candIdx,
        totalCandidates: candidates,
        messageIndex: cand.index,
        finishReason: cand.finishReason,
        finishMessage: cand.finishMessage,
        role: cand.message.role,
        usage: cand.usage,
        custom: cand.custom,
      });
      cand.message.content.forEach((part, partIdx) => {
        const partCounts = this.toPartCounts(
          partIdx,
          parts,
          candIdx,
          candidates
        );
        const initial = cand.finishMessage
          ? { finishMessage: this.toPartLogText(cand.finishMessage) }
          : {};
        logger.logStructured(`Output[${path}, ${model}] ${partCounts}`, {
          ...initial,
          ...sharedMetadata,
          content: this.toPartLogContent(part),
          partIndex: partIdx,
          totalParts: parts,
          candidateIndex: candIdx,
          totalCandidates: candidates,
          messageIndex: cand.index,
          finishReason: cand.finishReason,
        });
      });
      if (output.usage) {
        logger.logStructured(`Usage[${path}, ${model}]`, {
          ...sharedMetadata,
          usage: output.usage,
        });
      }
    });
  }

  private toPartCounts(
    partOrdinal: number,
    parts: number,
    msgOrdinal: number,
    messages: number
  ): string {
    if (parts > 1 && messages > 1) {
      return `(part ${this.xOfY(partOrdinal, parts)} in message ${this.xOfY(
        msgOrdinal,
        messages
      )})`;
    }
    if (parts > 1) {
      return `(part ${this.xOfY(partOrdinal, parts)})`;
    }
    if (messages > 1) {
      return `(message ${this.xOfY(msgOrdinal, messages)})`;
    }
    return '';
  }

  private xOfY(x: number, y: number): string {
    return `${x} of ${y}`;
  }

  private toPartLogContent(part: Part): string {
    if (part.text) {
      return this.toPartLogText(part.text);
    }
    if (part.media) {
      return this.toPartLogMedia(part);
    }
    if (part.toolRequest) {
      return this.toPartLogToolRequest(part);
    }
    if (part.toolResponse) {
      return this.toPartLogToolResponse(part);
    }
    return '<unknown format>';
  }

  private toPartLogText(text: string): string {
    return truncate(text, this.MAX_LOG_CONTENT_BYTES);
  }

  private toPartLogMedia(part: MediaPart): string {
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
    return this.toPartLogText(part.media.url);
  }

  private toPartLogToolRequest(part: ToolRequestPart): string {
    const inputText =
      typeof part.toolRequest.input === 'string'
        ? part.toolRequest.input
        : JSON.stringify(part.toolRequest.input);
    return this.toPartLogText(
      `Tool request: ${part.toolRequest.name}, ref: ${part.toolRequest.ref}, input: ${inputText}`
    );
  }

  private toPartLogToolResponse(part: ToolResponsePart): string {
    const outputText =
      typeof part.toolResponse.output === 'string'
        ? part.toolResponse.output
        : JSON.stringify(part.toolResponse.output);
    return this.toPartLogText(
      `Tool response: ${part.toolResponse.name}, ref: ${part.toolResponse.ref}, output: ${outputText}`
    );
  }

  /**
   * Records all metrics associated with performing a GenerateAction.
   */
  private doRecordGenerateActionMetrics(
    modelName: string,
    usage: GenerationUsage,
    dimensions: {
      flowName?: string;
      path?: string;
      temperature?: number;
      maxOutputTokens?: number;
      topK?: number;
      topP?: number;
      latencyMs?: number;
      errName?: string;
      source?: string;
      sourceVersion: string;
    }
  ) {
    const shared: SharedDimensions = {
      modelName: modelName,
      flowName: dimensions.flowName,
      path: dimensions.path,
      temperature: dimensions.temperature,
      topK: dimensions.topK,
      topP: dimensions.topP,
      source: dimensions.source,
      sourceVersion: dimensions.sourceVersion,
      status: dimensions.errName ? 'failure' : 'success',
    };

    this.actionCounter.add(1, {
      maxOutputTokens: dimensions.maxOutputTokens,
      error: dimensions.errName,
      ...shared,
    });

    this.latencies.record(dimensions.latencyMs, shared);

    // inputs
    this.inputTokens.add(usage.inputTokens, shared);
    this.inputCharacters.add(usage.inputCharacters, shared);
    this.inputImages.add(usage.inputImages, shared);
    this.inputVideos.add(usage.inputVideos, shared);
    this.inputAudio.add(usage.inputAudioFiles, shared);

    // outputs
    this.outputTokens.add(usage.outputTokens, shared);
    this.outputCharacters.add(usage.outputCharacters, shared);
    this.outputImages.add(usage.outputImages, shared);
    this.outputVideos.add(usage.outputVideos, shared);
    this.outputAudio.add(usage.outputAudioFiles, shared);
  }
}

const generateTelemetry = new GenerateTelemetry();
export { generateTelemetry };
