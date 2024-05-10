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

[plugins/pinecone/src/index.ts:94](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/pinecone/src/index.ts#L94)
