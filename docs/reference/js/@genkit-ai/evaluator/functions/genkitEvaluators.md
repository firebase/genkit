# Function: genkitEvaluators()

```ts
function genkitEvaluators<ModelCustomOptions, EmbedderCustomOptions>(params: PluginOptions<ModelCustomOptions, EmbedderCustomOptions>): EvaluatorAction<ZodObject<{
  "context": ZodOptional<ZodArray<ZodUnknown, "many">>;
  "input": ZodUnknown;
  "output": ZodOptional<ZodUnknown>;
  "reference": ZodOptional<ZodUnknown>;
  "testCaseId": ZodOptional<ZodString>;
  "traceIds": ZodOptional<ZodArray<ZodString, "many">>;
 }, "strip", ZodTypeAny, {
  "context": unknown[];
  "input": unknown;
  "output": unknown;
  "reference": unknown;
  "testCaseId": string;
  "traceIds": string[];
 }, {
  "context": unknown[];
  "input": unknown;
  "output": unknown;
  "reference": unknown;
  "testCaseId": string;
  "traceIds": string[];
 }>, ZodTypeAny>[]
```

Configures a Genkit evaluator

## Type parameters

| Type parameter |
| :------ |
| `ModelCustomOptions` *extends* `ZodType`\<`any`, `any`, `any`, `ModelCustomOptions`\> |
| `EmbedderCustomOptions` *extends* `ZodType`\<`any`, `any`, `any`, `EmbedderCustomOptions`\> |

## Parameters

| Parameter | Type |
| :------ | :------ |
| `params` | [`PluginOptions`](../interfaces/PluginOptions.md)\<`ModelCustomOptions`, `EmbedderCustomOptions`\> |

## Returns

`EvaluatorAction`\<`ZodObject`\<\{
  `"context"`: `ZodOptional`\<`ZodArray`\<`ZodUnknown`, `"many"`\>\>;
  `"input"`: `ZodUnknown`;
  `"output"`: `ZodOptional`\<`ZodUnknown`\>;
  `"reference"`: `ZodOptional`\<`ZodUnknown`\>;
  `"testCaseId"`: `ZodOptional`\<`ZodString`\>;
  `"traceIds"`: `ZodOptional`\<`ZodArray`\<`ZodString`, `"many"`\>\>;
 \}, `"strip"`, `ZodTypeAny`, \{
  `"context"`: `unknown`[];
  `"input"`: `unknown`;
  `"output"`: `unknown`;
  `"reference"`: `unknown`;
  `"testCaseId"`: `string`;
  `"traceIds"`: `string`[];
 \}, \{
  `"context"`: `unknown`[];
  `"input"`: `unknown`;
  `"output"`: `unknown`;
  `"reference"`: `unknown`;
  `"testCaseId"`: `string`;
  `"traceIds"`: `string`[];
 \}\>, `ZodTypeAny`\>[]

## Source

[plugins/evaluators/src/index.ts:98](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/plugins/evaluators/src/index.ts#L98)
