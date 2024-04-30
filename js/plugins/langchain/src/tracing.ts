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

import { BaseTracer, type Run } from '@langchain/core/tracers/base';
import {
  Span as ApiSpan,
  SpanStatusCode,
  context,
  trace,
} from '@opentelemetry/api';

const TRACER_NAME = 'genkit-tracer';
const TRACER_VERSION = 'v1';

export class GenkitTracer extends BaseTracer {
  spans: Record<string, ApiSpan> = {};
  tracer = trace.getTracer(TRACER_NAME, TRACER_VERSION);

  name = 'genkit_callback_handler' as const;

  protected persistRun(_run: Run) {
    return Promise.resolve();
  }

  getParents(run: Run) {
    const parents: Run[] = [];
    let currentRun = run;
    while (currentRun.parent_run_id) {
      const parent = this.runMap.get(currentRun.parent_run_id);
      if (parent) {
        parents.push(parent);
        currentRun = parent;
      } else {
        break;
      }
    }
    return parents;
  }

  getBreadcrumbs(run: Run) {
    const parents = this.getParents(run).reverse();
    return [...parents, run].map((parent) => `${parent.name}`).join('/');
  }

  private startSpan(run: Run) {
    let ctx;
    if (run.parent_run_id) {
      const parentCtx = this.spans[run.parent_run_id];
      ctx = trace.setSpan(context.active(), parentCtx);
    }
    const span = this.tracer.startSpan(run.name, undefined, ctx);
    console.log('run', JSON.stringify(run, undefined, '  '));
    if (run.inputs) {
      console.log('setting inputs', run.inputs);
      console.log(
        'setting inputs flattened',
        this.maybeFlattenInput(run.inputs)
      );
      span.setAttribute(
        'genkit:input',
        JSON.stringify(this.maybeFlattenInput(run.inputs))
      );
    }
    span.setAttribute('langchain:path', this.getBreadcrumbs(run));
    this.spans[run.id] = span;
    return span;
  }

  private endSpan(run: Run, attributes?: Record<string, string>) {
    const span = this.spans[run.id];
    span.setAttribute('genkit:state', run.error ? 'error' : 'success');
    if (run.error) {
      span.setStatus({
        code: SpanStatusCode.ERROR,
        message: run.error,
      });
    }
    if (run.outputs) {
      span.setAttribute(
        'genkit:output',
        JSON.stringify(this.maybeFlattenOutput(run.outputs))
      );
    }
    if (attributes) {
      span.setAttributes(attributes);
    }
    span.end();
    return span;
  }

  onChainStart(run: Run) {
    this.startSpan(run);
  }

  onChainEnd(run: Run) {
    this.endSpan(run);
  }

  onChainError(run: Run) {
    this.endSpan(run);
  }

  onLLMStart(run: Run) {
    this.startSpan(run);
  }

  onLLMEnd(run: Run) {
    this.endSpan(run);
  }

  onLLMError(run: Run) {
    this.endSpan(run);
  }

  onToolStart(run: Run) {
    this.startSpan(run);
  }

  onToolEnd(run: Run) {
    this.endSpan(run);
  }

  onToolError(run: Run) {
    this.endSpan(run);
  }

  onRetrieverStart(run: Run) {
    this.startSpan(run);
  }

  onRetrieverEnd(run: Run) {
    this.endSpan(run);
  }

  onRetrieverError(run: Run) {
    this.endSpan(run);
  }

  onAgentAction(run: Run) {
    this.startSpan(run);
    this.endSpan(run);
  }

  private maybeFlattenInput(input: any) {
    if (
      input &&
      input.hasOwnProperty('input') &&
      Object.keys(input).length === 1
    ) {
      return input.input;
    }
    return input;
  }

  private maybeFlattenOutput(output: any) {
    if (
      output &&
      output.hasOwnProperty('output') &&
      Object.keys(output).length === 1
    ) {
      return output.output;
    }
    return output;
  }
}
