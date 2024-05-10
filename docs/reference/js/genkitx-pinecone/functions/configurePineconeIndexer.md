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

[plugins/pinecone/src/index.ts:180](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/pinecone/src/index.ts#L180)
