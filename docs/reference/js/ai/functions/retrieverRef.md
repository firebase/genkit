# Function: retrieverRef()

```ts
function retrieverRef<CustomOptionsSchema>(options: RetrieverReference<CustomOptionsSchema>): RetrieverReference<CustomOptionsSchema>
```

Helper method to configure a [RetrieverReference](../interfaces/RetrieverReference.md) to a plugin.

## Type parameters

| Type parameter | Value |
| :------ | :------ |
| `CustomOptionsSchema` *extends* `ZodType`\<`any`, `any`, `any`, `CustomOptionsSchema`\> | `ZodTypeAny` |

## Parameters

| Parameter | Type |
| :------ | :------ |
| `options` | [`RetrieverReference`](../interfaces/RetrieverReference.md)\<`CustomOptionsSchema`\> |

## Returns

[`RetrieverReference`](../interfaces/RetrieverReference.md)\<`CustomOptionsSchema`\>

## Source

[ai/src/retriever.ts:269](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/ai/src/retriever.ts#L269)
