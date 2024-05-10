# Type alias: EvaluatorAction\<DataPoint, CustomOptions\>

```ts
type EvaluatorAction<DataPoint, CustomOptions>: Action<typeof EvalRequestSchema, typeof EvalResponsesSchema> & {
  "__configSchema": CustomOptions;
  "__dataPointType": DataPoint;
};
```

## Type declaration

| Member | Type |
| :------ | :------ |
| `__configSchema` | `CustomOptions` |
| `__dataPointType` | `DataPoint` |

## Type parameters

| Type parameter | Value |
| :------ | :------ |
| `DataPoint` *extends* *typeof* `BaseDataPointSchema` | *typeof* `BaseDataPointSchema` |
| `CustomOptions` *extends* `z.ZodTypeAny` | `z.ZodTypeAny` |

## Source

[ai/src/evaluator.ts:78](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/ai/src/evaluator.ts#L78)
