# Function: devLocalRetrieverRef()

```ts
function devLocalRetrieverRef(indexName: string): RetrieverReference<ZodOptional<ZodObject<{
  "k": ZodOptional<ZodNumber>;
 }, "strip", ZodTypeAny, {
  "k": number;
 }, {
  "k": number;
}>>>
```

Local file-based vectorstore retriever reference

## Parameters

| Parameter | Type |
| :------ | :------ |
| `indexName` | `string` |

## Returns

`RetrieverReference`\<`ZodOptional`\<`ZodObject`\<\{
  `"k"`: `ZodOptional`\<`ZodNumber`\>;
 \}, `"strip"`, `ZodTypeAny`, \{
  `"k"`: `number`;
 \}, \{
  `"k"`: `number`;
 \}\>\>\>

## Source

[plugins/dev-local-vectorstore/src/index.ts:92](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/plugins/dev-local-vectorstore/src/index.ts#L92)
