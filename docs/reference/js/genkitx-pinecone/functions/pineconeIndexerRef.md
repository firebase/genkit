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

[plugins/pinecone/src/index.ts:78](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/plugins/pinecone/src/index.ts#L78)
