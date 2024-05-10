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

[plugins/chroma/src/index.ts:86](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/chroma/src/index.ts#L86)
