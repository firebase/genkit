import * as z from 'zod';

// TODO: Temporarily here to get rid of the dependency on @genkit-ai/common.
// This will be replaced with a better interface.
export interface ActionMetadata<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
> {
  name: string;
  description?: string;
  inputSchema?: I;
  outputSchema?: O;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  metadata: Record<string, any>;
}

export class InternalError extends Error {
  constructor(msg: string) {
    super(msg);
  }
}

// Streaming callback function.
export type StreamingCallback<T> = (chunk: T) => void;
