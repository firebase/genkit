# Function: pineconeRetrieverRef()

```ts
function pineconeRetrieverRef(params: {
  "displayName": string;
  "indexId": string;
 }): RetrieverReference<ZodObject<{
  "filter": ZodOptional<ZodRecord<ZodString, ZodAny>>;
  "k": ZodNumber;
  "namespace": ZodOptional<ZodString>;
  "sparseVector": ZodOptional<ZodEffects<ZodObject<{
     "indices": ZodArray<ZodNumber, "many">;
     "values": ZodArray<ZodNumber, "many">;
    }, "strip", ZodTypeAny, {
     "indices": number[];
     "values": number[];
    }, {
     "indices": number[];
     "values": number[];
    }>, {
     "indices": number[];
     "values": number[];
    }, {
     "indices": number[];
     "values": number[];
    }>>;
 }, "strip", ZodTypeAny, {
  "filter": Record<string, any>;
  "k": number;
  "namespace": string;
  "sparseVector": {
     "indices": number[];
     "values": number[];
    };
 }, {
  "filter": Record<string, any>;
  "k": number;
  "namespace": string;
  "sparseVector": {
     "indices": number[];
     "values": number[];
    };
}>>
```

## Parameters

| Parameter | Type |
| :------ | :------ |
| `params` | `object` |
| `params.displayName`? | `string` |
| `params.indexId` | `string` |

## Returns

`RetrieverReference`\<`ZodObject`\<\{
  `"filter"`: `ZodOptional`\<`ZodRecord`\<`ZodString`, `ZodAny`\>\>;
  `"k"`: `ZodNumber`;
  `"namespace"`: `ZodOptional`\<`ZodString`\>;
  `"sparseVector"`: `ZodOptional`\<`ZodEffects`\<`ZodObject`\<\{
     `"indices"`: `ZodArray`\<`ZodNumber`, `"many"`\>;
     `"values"`: `ZodArray`\<`ZodNumber`, `"many"`\>;
    \}, `"strip"`, `ZodTypeAny`, \{
     `"indices"`: `number`[];
     `"values"`: `number`[];
    \}, \{
     `"indices"`: `number`[];
     `"values"`: `number`[];
    \}\>, \{
     `"indices"`: `number`[];
     `"values"`: `number`[];
    \}, \{
     `"indices"`: `number`[];
     `"values"`: `number`[];
    \}\>\>;
 \}, `"strip"`, `ZodTypeAny`, \{
  `"filter"`: `Record`\<`string`, `any`\>;
  `"k"`: `number`;
  `"namespace"`: `string`;
  `"sparseVector"`: \{
     `"indices"`: `number`[];
     `"values"`: `number`[];
    \};
 \}, \{
  `"filter"`: `Record`\<`string`, `any`\>;
  `"k"`: `number`;
  `"namespace"`: `string`;
  `"sparseVector"`: \{
     `"indices"`: `number`[];
     `"values"`: `number`[];
    \};
 \}\>\>

## Source

[plugins/pinecone/src/index.ts:65](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/pinecone/src/index.ts#L65)
