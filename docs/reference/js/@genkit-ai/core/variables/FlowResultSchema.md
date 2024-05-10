# Variable: FlowResultSchema

```ts
const FlowResultSchema: ZodIntersection<ZodObject<{
  "response": ZodNullable<ZodUnknown>;
 }, "strip", ZodTypeAny, {
  "response": unknown;
 }, {
  "response": unknown;
 }>, ZodObject<{
  "error": ZodOptional<ZodString>;
  "stacktrace": ZodOptional<ZodString>;
 }, "strip", ZodTypeAny, {
  "error": string;
  "stacktrace": string;
 }, {
  "error": string;
  "stacktrace": string;
}>>;
```

## Source

[core/src/flowTypes.ts:66](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/core/src/flowTypes.ts#L66)
