# Function: configurePineconeIndexer()

```ts
function configurePineconeIndexer<EmbedderCustomOptions>(params: {
  "clientParams": PineconeConfiguration;
  "embedder": EmbedderArgument<EmbedderCustomOptions>;
  "embedderOptions": TypeOf<EmbedderCustomOptions>;
  "indexId": string;
  "textKey": string;
 }): IndexerAction<ZodOptional<ZodObject<{
  "namespace": ZodOptional<ZodString>;
 }, "strip", ZodTypeAny, {
  "namespace": string;
 }, {
  "namespace": string;
}>>>
```

Configures a Pinecone indexer.

## Type parameters

| Type parameter |
| :------ |
| `EmbedderCustomOptions` *extends* `ZodType`\<`any`, `any`, `any`, `EmbedderCustomOptions`\> |

## Parameters

| Parameter | Type |
| :------ | :------ |
| `params` | `object` |
| `params.clientParams`? | `PineconeConfiguration` |
| `params.embedder` | `EmbedderArgument`\<`EmbedderCustomOptions`\> |
| `params.embedderOptions`? | `TypeOf`\<`EmbedderCustomOptions`\> |
| `params.indexId` | `string` |
| `params.textKey`? | `string` |

## Returns

`IndexerAction`\<`ZodOptional`\<`ZodObject`\<\{
  `"namespace"`: `ZodOptional`\<`ZodString`\>;
 \}, `"strip"`, `ZodTypeAny`, \{
  `"namespace"`: `string`;
 \}, \{
  `"namespace"`: `string`;
 \}\>\>\>

## Source

[plugins/pinecone/src/index.ts:180](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/plugins/pinecone/src/index.ts#L180)
