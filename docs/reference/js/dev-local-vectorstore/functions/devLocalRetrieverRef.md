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

[plugins/dev-local-vectorstore/src/index.ts:92](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/dev-local-vectorstore/src/index.ts#L92)
