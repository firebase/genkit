# Function: pineconeIndexerRef()

```ts
function pineconeIndexerRef(params: {
  "displayName": string;
  "indexId": string;
 }): IndexerReference<ZodOptional<ZodObject<{
  "namespace": ZodOptional<ZodString>;
 }, "strip", ZodTypeAny, {
  "namespace": string;
 }, {
  "namespace": string;
}>>>
```

## Parameters

| Parameter | Type |
| :------ | :------ |
| `params` | `object` |
| `params.displayName`? | `string` |
| `params.indexId` | `string` |

## Returns

`IndexerReference`\<`ZodOptional`\<`ZodObject`\<\{
  `"namespace"`: `ZodOptional`\<`ZodString`\>;
 \}, `"strip"`, `ZodTypeAny`, \{
  `"namespace"`: `string`;
 \}, \{
  `"namespace"`: `string`;
 \}\>\>\>

## Source

[plugins/pinecone/src/index.ts:78](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/pinecone/src/index.ts#L78)
