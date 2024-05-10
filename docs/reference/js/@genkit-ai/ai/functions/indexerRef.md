# Function: indexerRef()

```ts
function indexerRef<CustomOptionsSchema>(options: IndexerReference<CustomOptionsSchema>): IndexerReference<CustomOptionsSchema>
```

Helper method to configure a [IndexerReference](../interfaces/IndexerReference.md) to a plugin.

## Type parameters

| Type parameter | Value |
| :------ | :------ |
| `CustomOptionsSchema` *extends* `ZodType`\<`any`, `any`, `any`, `CustomOptionsSchema`\> | `ZodTypeAny` |

## Parameters

| Parameter | Type |
| :------ | :------ |
| `options` | [`IndexerReference`](../interfaces/IndexerReference.md)\<`CustomOptionsSchema`\> |

## Returns

[`IndexerReference`](../interfaces/IndexerReference.md)\<`CustomOptionsSchema`\>

## Source

[ai/src/retriever.ts:290](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/ai/src/retriever.ts#L290)
