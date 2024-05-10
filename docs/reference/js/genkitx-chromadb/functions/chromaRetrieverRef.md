# Function: chromaRetrieverRef()

```ts
function chromaRetrieverRef(params: {
  "collectionName": string;
  "displayName": string;
 }): RetrieverReference<ZodOptional<ZodObject<{
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

## Parameters

| Parameter | Type |
| :------ | :------ |
| `params` | `object` |
| `params.collectionName` | `string` |
| `params.displayName`? | `string` |

## Returns

`RetrieverReference`\<`ZodOptional`\<`ZodObject`\<\{
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

[plugins/chroma/src/index.ts:86](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/plugins/chroma/src/index.ts#L86)
