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

[core/src/flowTypes.ts:66](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/core/src/flowTypes.ts#L66)
