# Function: evaluatorRef()

```ts
function evaluatorRef<CustomOptionsSchema>(options: EvaluatorReference<CustomOptionsSchema>): EvaluatorReference<CustomOptionsSchema>
```

Helper method to configure a [EvaluatorReference](../interfaces/EvaluatorReference.md) to a plugin.

## Type parameters

| Type parameter | Value |
| :------ | :------ |
| `CustomOptionsSchema` *extends* `ZodType`\<`any`, `any`, `any`, `CustomOptionsSchema`\> | `ZodTypeAny` |

## Parameters

| Parameter | Type |
| :------ | :------ |
| `options` | [`EvaluatorReference`](../interfaces/EvaluatorReference.md)\<`CustomOptionsSchema`\> |

## Returns

[`EvaluatorReference`](../interfaces/EvaluatorReference.md)\<`CustomOptionsSchema`\>

## Source

[ai/src/evaluator.ts:262](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/ai/src/evaluator.ts#L262)
