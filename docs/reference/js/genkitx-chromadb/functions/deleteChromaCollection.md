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

[plugins/chroma/src/index.ts:289](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/plugins/chroma/src/index.ts#L289)
