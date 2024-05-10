# Variable: FlowStateExecutionSchema

```ts
const FlowStateExecutionSchema: z.ZodObject<{
  "endTime": z.ZodOptional<z.ZodNumber>;
  "startTime": z.ZodOptional<z.ZodNumber>;
  "traceIds": z.ZodArray<z.ZodString, "many">;
 }, "strip", z.ZodTypeAny, {
  "endTime": number;
  "startTime": number;
  "traceIds": string[];
 }, {
  "endTime": number;
  "startTime": number;
  "traceIds": string[];
}>;
```

## Type declaration

| Member | Type |
| :------ | :------ |
| `endTime` | `z.ZodOptional`\<`z.ZodNumber`\> |
| `startTime` | `z.ZodOptional`\<`z.ZodNumber`\> |
| `traceIds` | `z.ZodArray`\<`z.ZodString`, `"many"`\> |

## Source

core/lib/flowTypes.d.ts:35
