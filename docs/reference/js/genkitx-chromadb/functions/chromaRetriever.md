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

[plugins/chroma/src/index.ts:115](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/chroma/src/index.ts#L115)
