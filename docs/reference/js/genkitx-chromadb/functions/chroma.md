# Function: chroma()

```ts
function chroma<EmbedderCustomOptions>(params: {
  "clientParams": ChromaClientParams;
  "collectionName": string;
  "createCollectionIfMissing": boolean;
  "embedder": EmbedderArgument<EmbedderCustomOptions>;
  "embedderOptions": TypeOf<EmbedderCustomOptions>;
 }[]): PluginProvider
```

Chroma plugin that provides the Chroma retriever and indexer

## Type parameters

| Type parameter |
| :------ |
| `EmbedderCustomOptions` *extends* `ZodType`\<`any`, `any`, `any`, `EmbedderCustomOptions`\> |

## Parameters

| Parameter | Type |
| :------ | :------ |
| `params` | \{ `"clientParams"`: `ChromaClientParams`; `"collectionName"`: `string`; `"createCollectionIfMissing"`: `boolean`; `"embedder"`: `EmbedderArgument`\<`EmbedderCustomOptions`\>; `"embedderOptions"`: `TypeOf`\<`EmbedderCustomOptions`\>; \}[] |

## Returns

`PluginProvider`

## Source

[plugins/chroma/src/index.ts:57](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/chroma/src/index.ts#L57)
