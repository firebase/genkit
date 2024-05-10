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

[plugins/pinecone/src/index.ts:238](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/pinecone/src/index.ts#L238)
