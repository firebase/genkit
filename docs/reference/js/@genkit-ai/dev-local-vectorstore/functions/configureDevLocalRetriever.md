# Function: configureDevLocalRetriever()

```ts
function configureDevLocalRetriever<EmbedderCustomOptions>(params: {
  "embedder": EmbedderArgument<EmbedderCustomOptions>;
  "embedderOptions": TypeOf<EmbedderCustomOptions>;
  "indexName": string;
 }): RetrieverAction<ZodObject<{
  "k": ZodOptional<ZodNumber>;
 }, "strip", ZodTypeAny, {
  "k": number;
 }, {
  "k": number;
}>>
```

Configures a local vectorstore retriever

## Type parameters

| Type parameter |
| :------ |
| `EmbedderCustomOptions` *extends* `ZodType`\<`any`, `any`, `any`, `EmbedderCustomOptions`\> |

## Parameters

| Parameter | Type |
| :------ | :------ |
| `params` | `object` |
| `params.embedder` | `EmbedderArgument`\<`EmbedderCustomOptions`\> |
| `params.embedderOptions`? | `TypeOf`\<`EmbedderCustomOptions`\> |
| `params.indexName` | `string` |

## Returns

`RetrieverAction`\<`ZodObject`\<\{
  `"k"`: `ZodOptional`\<`ZodNumber`\>;
 \}, `"strip"`, `ZodTypeAny`, \{
  `"k"`: `number`;
 \}, \{
  `"k"`: `number`;
 \}\>\>

## Source

[plugins/dev-local-vectorstore/src/index.ts:170](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/plugins/dev-local-vectorstore/src/index.ts#L170)
