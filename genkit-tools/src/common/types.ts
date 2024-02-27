import { JSONSchema7Type } from 'json-schema';

/**
 * Schema of a runnable action (e.g. text-llm, flow, etc).
 */
export interface ActionSchema {
  /**
   * Key consists of action type (e.g. text-llm) and a unique ID (e.g. provider/model).
   */
  key: string;
  name: string;
  description?: string;
  inputSchema?: JSONSchema7Type;
  outputSchema?: JSONSchema7Type;
  metadata: any;
}
