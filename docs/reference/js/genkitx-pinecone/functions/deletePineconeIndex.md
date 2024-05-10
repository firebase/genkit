# Function: deletePineconeIndex()

```ts
function deletePineconeIndex(params: {
  "clientParams": PineconeConfiguration;
  "name": string;
}): Promise<void>
```

Helper function for deleting Chroma collections.

## Parameters

| Parameter | Type |
| :------ | :------ |
| `params` | `object` |
| `params.clientParams`? | `PineconeConfiguration` |
| `params.name` | `string` |

## Returns

`Promise`\<`void`\>

## Source

[plugins/pinecone/src/index.ts:262](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/plugins/pinecone/src/index.ts#L262)
