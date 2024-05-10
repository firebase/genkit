# Function: createChromaCollection()

```ts
function createChromaCollection<EmbedderCustomOptions>(params: {
  "clientParams": ChromaClientParams;
  "embedder": EmbedderArgument<EmbedderCustomOptions>;
  "embedderOptions": TypeOf<EmbedderCustomOptions>;
  "metadata": CollectionMetadata;
  "name": string;
}): Promise<Collection>
```

Helper function for creating Chroma collections.

## Type parameters

| Type parameter |
| :------ |
| `EmbedderCustomOptions` *extends* `ZodType`\<`any`, `any`, `any`, `EmbedderCustomOptions`\> |

## Parameters

| Parameter | Type |
| :------ | :------ |
| `params` | `object` |
| `params.clientParams`? | `ChromaClientParams` |
| `params.embedder`? | `EmbedderArgument`\<`EmbedderCustomOptions`\> |
| `params.embedderOptions`? | `TypeOf`\<`EmbedderCustomOptions`\> |
| `params.metadata`? | `CollectionMetadata` |
| `params.name` | `string` |

## Returns

`Promise`\<`Collection`\>

## Source

[plugins/chroma/src/index.ts:253](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/chroma/src/index.ts#L253)
