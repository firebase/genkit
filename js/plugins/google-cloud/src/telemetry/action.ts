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

import { logger } from 'genkit/logging';
import { toDisplayPath, type PathMetadata } from 'genkit/tracing';
import { type Telemetry } from '../metrics.js';
import {
  createCommonLogAttributes,
  extractOuterFeatureNameFromPath,
  truncate,
  truncatePath,
} from '../utils.js';
import type { ReadableSpan } from '@opentelemetry/sdk-trace-base';

class ActionTelemetry implements Telemetry {
  tick(
    span: ReadableSpan,
    paths: Set<PathMetadata>,
    logInputAndOutput: boolean,
    projectId?: string
  ): void {
    const attributes = span.attributes;

    const actionName = (attributes['genkit:name'] as string) || '<unknown>';
    const subtype = attributes['genkit:metadata:subtype'] as string;
    const path = (attributes['genkit:path'] as string) || '<unknown>';
    let featureName = extractOuterFeatureNameFromPath(path);
    if (!featureName || featureName === '<unknown>') {
      featureName = actionName;
    }

    if (subtype === 'tool' && logInputAndOutput) {
      const input = truncate(attributes['genkit:input'] as string);
      const output = truncate(attributes['genkit:output'] as string);
      const sessionId = attributes['genkit:sessionId'] as string;
      const threadName = attributes['genkit:threadName'] as string;

      if (input) {
        this.writeLog(
          span,
          'Input',
          featureName,
          path,
          input,
          projectId,
          sessionId,
          threadName
        );
      }
      if (output) {
        this.writeLog(
          span,
          'Output',
          featureName,
          path,
          output,
          projectId,
          sessionId,
          threadName
        );
      }
    }
  }

  private writeLog(
    span: ReadableSpan,
    tag: string,
    featureName: string,
    qualifiedPath: string,
    content: string,
    projectId?: string,
    sessionId?: string,
    threadName?: string
  ) {
    const path = truncatePath(toDisplayPath(qualifiedPath));
    const sharedMetadata = {
      ...createCommonLogAttributes(span, projectId),
      path,
      qualifiedPath,
      featureName,
      sessionId,
      threadName,
    };
    logger.logStructured(`${tag}[${path}, ${featureName}]`, {
      ...sharedMetadata,
      content,
    });
  }
}

const actionTelemetry = new ActionTelemetry();
export { actionTelemetry };
