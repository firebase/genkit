# Function: pinecone()

```ts
function pinecone<EmbedderCustomOptions>(params: {
  "clientParams": PineconeConfiguration;
  "embedder": EmbedderArgument<EmbedderCustomOptions>;
  "embedderOptions": TypeOf<EmbedderCustomOptions>;
  "indexId": string;
 }[]): PluginProvider
```

Pinecone plugin that provides a pinecone retriever and indexer

## Type parameters

| Type parameter |
| :------ |
| `EmbedderCustomOptions` *extends* `ZodType`\<`any`, `any`, `any`, `EmbedderCustomOptions`\> |

## Parameters

| Parameter | Type |
| :------ | :------ |
| `params` | \{ `"clientParams"`: `PineconeConfiguration`; `"embedder"`: `EmbedderArgument`\<`EmbedderCustomOptions`\>; `"embedderOptions"`: `TypeOf`\<`EmbedderCustomOptions`\>; `"indexId"`: `string`; \}[] |

## Returns

`PluginProvider`

## Source

[plugins/pinecone/src/index.ts:94](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/plugins/pinecone/src/index.ts#L94)
