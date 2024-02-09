import * as z from 'zod';

// TODO: Temporarily here to get rid of the dependency on @google-genkit/common.
// This will be replaced with a better interface.
export interface ActionMetadata<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
> {
  name: string;
  description?: string;
  inputSchema?: I;
  outputSchema?: O;
  metadata: Record<string, any>;
}
