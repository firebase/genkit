import * as z from 'zod';

export const AnalyticsInfoSchema = z.union([
  z.object({ enabled: z.literal(false) }),
  z.object({
    enabled: z.literal(true),
    property: z.string(),
    measurementId: z.string(),
    apiSecret: z.string(),
    clientId: z.string(),
    sessionId: z.string(),
    debug: z.object({
      debugMode: z.boolean(),
      validateOnly: z.boolean(),
    }),
  }),
]);

export type AnalyticsInfo = z.infer<typeof AnalyticsInfoSchema>;
