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

[plugins/pinecone/src/index.ts:262](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/pinecone/src/index.ts#L262)
