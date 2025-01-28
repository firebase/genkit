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

import { Action } from '@genkit-ai/core';
import {
  runFlow as baseRunFlow,
  streamFlow as baseStreamFlow,
} from 'genkit/client';
import * as z from 'zod';

// Helper for z.infer that asserts Z is a zod type;
type ZodToTS<Z> = Z extends z.ZodAny ? z.infer<Z> : never;

type Input<A extends Action> =
  A extends Action<infer I, any, any> ? ZodToTS<I> : never;
type Output<A extends Action> =
  A extends Action<any, infer O, any> ? ZodToTS<O> : never;
type Stream<A extends Action> =
  A extends Action<any, any, infer S> ? ZodToTS<S> : never;

export interface RequestData {
  url: string;
  headers?: Record<string, string>;
}

export function runFlow<A extends Action = Action>(
  url: string,
  data: Input<A>
): Promise<Output<A>>;
export function runFlow<A extends Action = Action>(
  req: RequestData,
  data: Input<A>
): Promise<Output<A>>;
export function runFlow<A extends Action = Action>(
  req: string | RequestData,
  data: Input<A>
): Promise<Output<A>> {
  if (typeof req === 'string') {
    return baseRunFlow<Output<A>>({ url: req, input: data });
  } else {
    return baseRunFlow<Output<A>>({ ...req, input: data });
  }
}

export interface StreamResponse<A extends Action> {
  output: Promise<Output<A>>;
  stream: AsyncIterable<Stream<A>>;
}

export function streamFlow<A extends Action = Action>(
  url: string,
  data: Input<A>
): StreamResponse<A>;
export function streamFlow<A extends Action = Action>(
  req: RequestData,
  data: Input<A>
): StreamResponse<A>;
export function streamFlow<A extends Action = Action>(
  req: string | RequestData,
  data: Input<A>
): StreamResponse<A> {
  if (typeof req === 'string') {
    const res = baseStreamFlow<Output<A>, Stream<A>>({ url: req, input: data });
    return {
      output: res.output(),
      stream: res.stream(),
    };
  } else {
    const res = baseStreamFlow<Output<A>, Stream<A>>({ ...req, input: data });
    return {
      output: res.output(),
      stream: res.stream(),
    };
  }
}
