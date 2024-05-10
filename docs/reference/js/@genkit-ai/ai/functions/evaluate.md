# Function: evaluate()

```ts
function evaluate<DataPoint, EvaluatorOptions>(params: {
  "dataset": Dataset<DataPoint>;
  "evaluator": EvaluatorArgument<DataPoint, EvaluatorOptions>;
  "options": TypeOf<EvaluatorOptions>;
}): Promise<any[]>
```

A veneer for interacting with evaluators.

## Type parameters

| Type parameter | Value |
| :------ | :------ |
| `DataPoint` *extends* `ZodObject`\<\{
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
 \}, `DataPoint`\> | `ZodObject`\<\{
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
 \}\> |
| `EvaluatorOptions` *extends* `ZodType`\<`any`, `any`, `any`, `EvaluatorOptions`\> | `ZodTypeAny` |

## Parameters

| Parameter | Type |
| :------ | :------ |
| `params` | `object` |
| `params.dataset` | `Dataset`\<`DataPoint`\> |
| `params.evaluator` | `EvaluatorArgument`\<`DataPoint`, `EvaluatorOptions`\> |
| `params.options`? | `TypeOf`\<`EvaluatorOptions`\> |

## Returns

`Promise`\<`any`[]\>

## Source

[ai/src/evaluator.ts:218](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/ai/src/evaluator.ts#L218)
