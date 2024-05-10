# Function: configurePineconeRetriever()

```ts
function configurePineconeRetriever<EmbedderCustomOptions>(params: {
  "clientParams": PineconeConfiguration;
  "embedder": EmbedderArgument<EmbedderCustomOptions>;
  "embedderOptions": TypeOf<EmbedderCustomOptions>;
  "indexId": string;
  "textKey": string;
 }): RetrieverAction<ZodObject<{
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

Configures a Pinecone retriever.

## Type parameters

| Type parameter |
| :------ |
| `EmbedderCustomOptions` *extends* `ZodType`\<`any`, `any`, `any`, `EmbedderCustomOptions`\> |

## Parameters

| Parameter | Type |
| :------ | :------ |
| `params` | `object` |
| `params.clientParams`? | `PineconeConfiguration` |
| `params.embedder` | `EmbedderArgument`\<`EmbedderCustomOptions`\> |
| `params.embedderOptions`? | `TypeOf`\<`EmbedderCustomOptions`\> |
| `params.indexId` | `string` |
| `params.textKey`? | `string` |

## Returns

`RetrieverAction`\<`ZodObject`\<\{
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

[plugins/pinecone/src/index.ts:125](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/plugins/pinecone/src/index.ts#L125)
