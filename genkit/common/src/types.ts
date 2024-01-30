import * as z from "zod";
import { SPAN_TYPE_ATTR, runInNewSpan } from "./tracing";

export interface ActionMetadata<I extends z.ZodTypeAny, O extends z.ZodTypeAny> {
  name: string;
  description?: string;
  inputSchema?: I;
  outputSchema?: O;
}

export type Action<I extends z.ZodTypeAny, O extends z.ZodTypeAny> = ((
  input: z.infer<I>
) => Promise<z.infer<O>>) & { __action: ActionMetadata<I, O> };

export type SideChannelData = Record<string, any>;

/**
 *
 */
export function action<I extends z.ZodTypeAny, O extends z.ZodTypeAny>(
  config: {
    name: string;
    description?: string;
    input?: I;
    output?: O;
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
          [SPAN_TYPE_ATTR]: "action",
        },
      },
      async (metadata) => {
        metadata.name = config.name;
        metadata.input = input;
        try {
          const output = fn(input);
          metadata.output = output;
          metadata.state = "success";
          return output;
        } catch (e) {
          metadata.state = "error";
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
  };
  return actionFn;
}
