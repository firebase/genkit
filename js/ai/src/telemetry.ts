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

import { MetricHistogram } from '@genkit-ai/core';
import { SpanMetadata, getTelemetryConfig } from '@genkit-ai/core/tracing';
import { AttributeValue, ValueType } from '@opentelemetry/api';
import { GenerateResponseData } from './model.js';
import { logger } from '@genkit-ai/core/logging';

const tokenUsage = new MetricHistogram('gen_ai.client.token.usage', {
  description: 'Usage of GenAI tokens.',
  valueType: ValueType.INT,
  unit: 'token',
});

const operationDuration = new MetricHistogram(
  'gen_ai.client.operation.duration',
  {
    description: 'Time taken for GenAI operations',
    valueType: ValueType.DOUBLE,
    unit: 'token',
  }
);

export async function writeSemConvTelemetry(
  output: GenerateResponseData,
  span?: SpanMetadata
): Promise<void> {
  const telemetryConfig = await getTelemetryConfig();
  console.log(`>>> TelemetryConfig: ${JSON.stringify(telemetryConfig?.semConv)}`);

  if (telemetryConfig?.semConv?.writeMetrics) {
    writeMetrics(output);
  }
  if (span && telemetryConfig?.semConv?.writeSpanAttributes) {
    writeSpanAttributes(output, span);
  }
  if (span && telemetryConfig?.semConv?.writeLogEvents) {
    writeEvents(output, span);
  }
}

function writeMetrics(resp: GenerateResponseData): void {
  const commonDimensions = {
    'gen_ai.client.framework': 'genkit',
    'gen_ai.operation.name': resp.clientTelemetry?.operationName,
    'gen_ai.system': resp.clientTelemetry?.system,
    'gen_ai.request.model': resp.clientTelemetry?.requestModel,
    'server.port': resp.clientTelemetry?.serverPort,
    'gen_ai.response.model': resp.clientTelemetry?.responseModel,
    'server.address': resp.clientTelemetry?.serverAddress,
  };
  tokenUsage.record(resp.usage?.inputTokens || 0, {
    ...commonDimensions,
    'gen_ai.token.type': 'input',
  });
  tokenUsage.record(resp.usage?.outputTokens || 0, {
    ...commonDimensions,
    'gen_ai.token.type': 'output',
  });
  if (resp.latencyMs) {
    operationDuration.record(resp.latencyMs, commonDimensions);
  }
}

function writeSpanAttributes(
  output: GenerateResponseData,
  span: SpanMetadata
): void {
  const t: Record<string, AttributeValue> = {};
  const client = output.clientTelemetry;
  const config = output.request?.config;
  const usage = output.usage;
  setAttribute(t, 'gen_ai.client.framework', 'genkit');
  setAttribute(t, 'gen_ai.operation.name', client?.operationName);
  setAttribute(t, 'gen_ai.system', client?.system);
  setAttribute(t, 'gen_ai.request.model', client?.requestModel);
  setAttribute(t, 'server.port', client?.serverPort);
  setAttribute(t, 'gen_ai.request.encoding_formats', client?.encodingFormats);
  setAttribute(t, 'gen_ai.request.frequency_penalty', config?.frequencyPenalty);
  setAttribute(t, 'gen_ai.request.max_tokens', config?.maxOutputTokens);
  setAttribute(t, 'gen_ai.request.presence_penalty', config?.presencePenalty);
  setAttribute(t, 'gen_ai.request.stop_sequences', config?.stopSequences);
  setAttribute(t, 'gen_ai.request.temperature', config?.temperature);
  setAttribute(t, 'gen_ai.request.top_k', config?.topK);
  setAttribute(t, 'gen_ai.request.top_p', config?.topP);
  setAttribute(t, 'gen_ai.response.finish_reasons', [output.finishReason]);
  setAttribute(t, 'gen_ai.response.id', client?.responseId);
  setAttribute(t, 'gen_ai.response.model', client?.responseModel);
  setAttribute(t, 'gen_ai.usage.input_tokens', usage?.inputTokens);
  setAttribute(t, 'gen_ai.usage.output_tokens', usage?.outputTokens);
  setAttribute(t, 'server.address', client?.serverAddress);
  span.telemetry = t;
}

function setAttribute(
  attrs: Record<string, AttributeValue>,
  key: string,
  attribute?: AttributeValue
) {
  if (attribute) {
    attrs[key] = attribute!;
  }
}

function writeEvents(output: GenerateResponseData, span: SpanMetadata) {
  const baseMsg = {
    gen_ai: {
      system: output.clientTelemetry?.system
    }
  }
  output.request?.messages.forEach((msg) => {
    const role = msg.role.replace('model', 'assistant');
    logger.logStructured(`gen_ai.${role}.message`, {
      ...baseMsg,
      role,
      content: msg.content,
    });
  });
  if (output.clientTelemetry?.operationName === "chat") {
    logger.logStructured('gen_ai.choice', {
      ...baseMsg,
      finish_reason: output.finishReason,
      index: 0,
      message: {
        role: output.message?.role,
        content: output.message?.content,
      }
    });
  } else if (output.message) {
    const role = output.message?.role.replace('model', 'assistant');
    logger.logStructured(`gen_ai.${role}.message`, {
      ...baseMsg,
      role,
      content: output.message?.content,
    });
  }
}
