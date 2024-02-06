import * as z from 'zod';
import { SPAN_TYPE_ATTR, runInNewSpan } from './tracing';

export interface ActionMetadata<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  M extends Record<string, any> = Record<string, any>
> {
  name: string;
  description?: string;
  inputSchema?: I;
  outputSchema?: O;
  metadata?: M;
}

export type Action<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  M extends Record<string, any> = Record<string, any>
> = ((input: z.infer<I>) => Promise<z.infer<O>>) & {
  __action: ActionMetadata<I, O, M>;
};

export type SideChannelData = Record<string, any>;

/**
 *
 */
export function action<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  M extends Record<string, any> = Record<string, any>
>(
  config: {
    name: string;
    description?: string;
    input?: I;
    output?: O;
    metadata?: M;
  },
  fn: (input: z.infer<I>) => Promise<z.infer<O>>
): Action<I, O> {
  const actionFn = async (input: I) => {
    if (config.input) {
      input = config.input.parse(input);
    }
    let output = await runInNewSpan(
      {
        metadata: {
          name: config.name,
        },
        labels: {
          [SPAN_TYPE_ATTR]: 'action',
        },
      },
      async (metadata) => {
        metadata.name = config.name;
        metadata.input = input;
        try {
          const output = fn(input);
          metadata.output = output;
          metadata.state = 'success';
          return output;
        } catch (e) {
          metadata.state = 'error';
          throw e;
        }
      }
    );
    if (config.output) {
      output = config.output.parse(output);
    }
    return output;
  };
  actionFn.__action = {
    name: config.name,
    description: config.description,
    inputSchema: config.input,
    outputSchema: config.output,
    metadata: config.metadata,
  };
  return actionFn;
}
