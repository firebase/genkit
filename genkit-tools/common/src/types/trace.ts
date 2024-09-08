import { extendZodWithOpenApi } from '@asteasolutions/zod-to-openapi';
import { SpanData, SpanDataSchema } from '@genkit-ai/telemetry-server';
import * as z from 'zod';

export {
  InstrumentationLibrarySchema,
  LinkSchema,
  SpanContextSchema,
  SpanData,
  SpanDataSchema,
  SpanMetadata,
  SpanMetadataSchema,
  SpanStatusSchema,
  TimeEventSchema,
  TraceData,
  TraceDataSchema,
} from '@genkit-ai/telemetry-server';

extendZodWithOpenApi(z);

export const NestedSpanDataSchema = SpanDataSchema.extend({
  spans: z.lazy(() => z.array(SpanDataSchema)),
});

export type NestedSpanData = z.infer<typeof SpanDataSchema> & {
  spans?: SpanData[];
};
