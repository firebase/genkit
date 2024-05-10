# Function: deleteChromaCollection()

```ts
function deleteChromaCollection(params: {
  "clientParams": ChromaClientParams;
  "name": string;
}): Promise<void>
```

Helper function for deleting Chroma collections.

## Parameters

| Parameter | Type |
| :------ | :------ |
| `params` | `object` |
| `params.clientParams`? | `ChromaClientParams` |
| `params.name` | `string` |

## Returns

`Promise`\<`void`\>

## Source

[plugins/chroma/src/index.ts:289](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/chroma/src/index.ts#L289)
