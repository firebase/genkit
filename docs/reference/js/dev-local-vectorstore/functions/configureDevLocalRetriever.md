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

[plugins/dev-local-vectorstore/src/index.ts:170](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/dev-local-vectorstore/src/index.ts#L170)
