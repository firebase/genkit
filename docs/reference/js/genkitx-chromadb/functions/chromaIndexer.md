# Function: chromaIndexer()

```ts
function chromaIndexer<EmbedderCustomOptions>(params: {
  "clientParams": ChromaClientParams;
  "collectionName": string;
  "createCollectionIfMissing": boolean;
  "embedder": EmbedderArgument<EmbedderCustomOptions>;
  "embedderOptions": TypeOf<EmbedderCustomOptions>;
  "textKey": string;
}): IndexerAction<ZodOptional<ZodNull>>
```

Configures a Chroma indexer.

## Type parameters

| Type parameter |
| :------ |
| `EmbedderCustomOptions` *extends* `ZodType`\<`any`, `any`, `any`, `EmbedderCustomOptions`\> |

## Parameters

| Parameter | Type |
| :------ | :------ |
| `params` | `object` |
| `params.clientParams`? | `ChromaClientParams` |
| `params.collectionName` | `string` |
| `params.createCollectionIfMissing`? | `boolean` |
| `params.embedder` | `EmbedderArgument`\<`EmbedderCustomOptions`\> |
| `params.embedderOptions`? | `TypeOf`\<`EmbedderCustomOptions`\> |
| `params.textKey`? | `string` |

## Returns

`IndexerAction`\<`ZodOptional`\<`ZodNull`\>\>

## Source

[plugins/chroma/src/index.ts:185](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/chroma/src/index.ts#L185)
