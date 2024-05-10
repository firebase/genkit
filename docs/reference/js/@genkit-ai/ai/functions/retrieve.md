# Function: retrieve()

```ts
function retrieve<CustomOptions>(params: RetrieverParams<CustomOptions>): Promise<Document[]>
```

Retrieves documents from a [RetrieverAction](../type-aliases/RetrieverAction.md) based on the provided query.

## Type parameters

| Type parameter |
| :------ |
| `CustomOptions` *extends* `ZodType`\<`any`, `any`, `any`, `CustomOptions`\> |

## Parameters

| Parameter | Type |
| :------ | :------ |
| `params` | `RetrieverParams`\<`CustomOptions`\> |

## Returns

`Promise`\<`Document`[]\>

## Source

[ai/src/retriever.ts:203](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/ai/src/retriever.ts#L203)
