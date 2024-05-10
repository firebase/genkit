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

[ai/src/evaluator.ts:78](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/ai/src/evaluator.ts#L78)
