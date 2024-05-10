# Function: describePineconeIndex()

```ts
function describePineconeIndex(params: {
  "clientParams": PineconeConfiguration;
  "name": string;
}): Promise<IndexModel>
```

Helper function to describe a Pinecone index. Use it to check if a newly created index is ready for use.

## Parameters

| Parameter | Type |
| :------ | :------ |
| `params` | `object` |
| `params.clientParams`? | `PineconeConfiguration` |
| `params.name` | `string` |

## Returns

`Promise`\<`IndexModel`\>

## Source

[plugins/pinecone/src/index.ts:250](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/pinecone/src/index.ts#L250)
