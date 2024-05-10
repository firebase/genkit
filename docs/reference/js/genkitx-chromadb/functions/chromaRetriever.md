# Function: chromaRetriever()

```ts
function chromaRetriever<EmbedderCustomOptions>(params: {
  "clientParams": ChromaClientParams;
  "collectionName": string;
  "createCollectionIfMissing": boolean;
  "embedder": EmbedderArgument<EmbedderCustomOptions>;
  "embedderOptions": TypeOf<EmbedderCustomOptions>;
 }): RetrieverAction<ZodOptional<ZodObject<{
  "include": ZodOptional<ZodArray<ZodNativeEnum<typeof IncludeEnum>, "many">>;
  "k": ZodOptional<ZodNumber>;
  "where": ZodOptional<ZodType<Where, ZodTypeDef, Where>>;
  "whereDocument": ZodOptional<ZodType<WhereDocument, ZodTypeDef, WhereDocument>>;
 }, "strip", ZodTypeAny, {
  "include": IncludeEnum[];
  "k": number;
  "where": Where;
  "whereDocument": WhereDocument;
 }, {
  "include": IncludeEnum[];
  "k": number;
  "where": Where;
  "whereDocument": WhereDocument;
}>>>
```

Configures a Chroma vector store retriever.

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

## Returns

`RetrieverAction`\<`ZodOptional`\<`ZodObject`\<\{
  `"include"`: `ZodOptional`\<`ZodArray`\<`ZodNativeEnum`\<*typeof* [`IncludeEnum`](../enumerations/IncludeEnum.md)\>, `"many"`\>\>;
  `"k"`: `ZodOptional`\<`ZodNumber`\>;
  `"where"`: `ZodOptional`\<`ZodType`\<`Where`, `ZodTypeDef`, `Where`\>\>;
  `"whereDocument"`: `ZodOptional`\<`ZodType`\<`WhereDocument`, `ZodTypeDef`, `WhereDocument`\>\>;
 \}, `"strip"`, `ZodTypeAny`, \{
  `"include"`: [`IncludeEnum`](../enumerations/IncludeEnum.md)[];
  `"k"`: `number`;
  `"where"`: `Where`;
  `"whereDocument"`: `WhereDocument`;
 \}, \{
  `"include"`: [`IncludeEnum`](../enumerations/IncludeEnum.md)[];
  `"k"`: `number`;
  `"where"`: `Where`;
  `"whereDocument"`: `WhereDocument`;
 \}\>\>\>

## Source

[plugins/chroma/src/index.ts:115](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/plugins/chroma/src/index.ts#L115)
