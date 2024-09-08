import { extendZodWithOpenApi } from '@asteasolutions/zod-to-openapi';
import * as z from 'zod';

extendZodWithOpenApi(z);

/**
 * Trace store list query.
 */
export interface TraceQuery {
  limit?: number;
  continuationToken?: string;
}

/**
 * Response from trace store list query.
 */
export interface TraceQueryResponse {
  traces: TraceData[];
  continuationToken?: string;
}

/**
 * Trace store interface.
 */
export interface TraceStore {
  save(traceId: string, trace: TraceData): Promise<void>;
  load(traceId: string): Promise<TraceData | undefined>;
  list(query?: TraceQuery): Promise<TraceQueryResponse>;
}

// NOTE: Keep this file in sync with genkit/common/src/tracing/types.ts!
// Eventually tools will be source of truth for these types (by generating a
// JSON schema) but until then this file must be manually kept in sync

export const SpanMetadataSchema = z.object({
  name: z.string(),
  state: z.enum(['success', 'error']).optional(),
  input: z.unknown().optional(),
  output: z.unknown().optional(),
  isRoot: z.boolean().optional(),
  metadata: z.record(z.string(), z.string()).optional(),
});
export type SpanMetadata = z.infer<typeof SpanMetadataSchema>;

export const SpanStatusSchema = z.object({
  code: z.number(),
  message: z.string().optional(),
});

export const TimeEventSchema = z.object({
  time: z.number(),
  annotation: z.object({
    attributes: z.record(z.string(), z.unknown()),
    description: z.string(),
  }),
});

export const SpanContextSchema = z.object({
  traceId: z.string(),
  spanId: z.string(),
  isRemote: z.boolean().optional(),
  traceFlags: z.number(),
});

export const LinkSchema = z.object({
  context: SpanContextSchema.optional(),
  attributes: z.record(z.string(), z.unknown()).optional(),
  droppedAttributesCount: z.number().optional(),
});

export const InstrumentationLibrarySchema = z.object({
  name: z.string().readonly(),
  version: z.string().optional().readonly(),
  schemaUrl: z.string().optional().readonly(),
});

export const SpanDataSchema = z
  .object({
    spanId: z.string(),
    traceId: z.string(),
    parentSpanId: z.string().optional(),
    startTime: z.number(),
    endTime: z.number(),
    attributes: z.record(z.string(), z.unknown()),
    displayName: z.string(),
    links: z.array(LinkSchema).optional(),
    instrumentationLibrary: InstrumentationLibrarySchema,
    spanKind: z.string(),
    sameProcessAsParentSpan: z.object({ value: z.boolean() }).optional(),
    status: SpanStatusSchema.optional(),
    timeEvents: z
      .object({
        timeEvent: z.array(TimeEventSchema).optional(),
      })
      .optional(),
    truncated: z.boolean().optional(),
  })
  .openapi('SpanData');

export type SpanData = z.infer<typeof SpanDataSchema>;

export const TraceDataSchema = z
  .object({
    traceId: z.string(),
    displayName: z.string().optional(),
    startTime: z.number().optional(),
    endTime: z.number().optional(),
    spans: z.record(z.string(), SpanDataSchema),
  })
  .openapi('TraceData');

export type TraceData = z.infer<typeof TraceDataSchema>;
