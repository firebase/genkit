# Function: createPineconeIndex()

```ts
function createPineconeIndex(params: {
  "clientParams": PineconeConfiguration;
  "options": CreateIndexOptions;
}): Promise<void | IndexModel>
```

Helper function for creating a Pinecone index.

## Parameters

| Parameter | Type |
| :------ | :------ |
| `params` | `object` |
| `params.clientParams`? | `PineconeConfiguration` |
| `params.options` | `CreateIndexOptions` |

## Returns

`Promise`\<`void` \| `IndexModel`\>

## Source

[plugins/pinecone/src/index.ts:238](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/plugins/pinecone/src/index.ts#L238)
