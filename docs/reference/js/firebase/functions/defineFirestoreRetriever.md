# Function: defineFirestoreRetriever()

```ts
function defineFirestoreRetriever(config: {
  "collection": string;
  "contentField": string | (snap: QueryDocumentSnapshot<DocumentData, DocumentData>) => ({
     "media": undefined;
     "text": string;
    } | {
     "media": {
        "contentType": string;
        "url": string;
       };
     "text": undefined;
    })[];
  "distanceMeasure": "EUCLIDEAN" | "COSINE" | "DOT_PRODUCT";
  "embedder": EmbedderArgument<ZodTypeAny>;
  "firestore": Firestore;
  "label": string;
  "metadataFields": string[] | (snap: QueryDocumentSnapshot<DocumentData, DocumentData>) => Record<string, any>;
  "name": string;
  "vectorField": string;
 }): RetrieverAction<ZodObject<{
  "limit": ZodNumber;
  "where": ZodOptional<ZodRecord<ZodString, ZodAny>>;
 }, "strip", ZodTypeAny, {
  "limit": number;
  "where": Record<string, any>;
 }, {
  "limit": number;
  "where": Record<string, any>;
}>>
```

Define a retriever that uses vector similarity search to retrieve documents from Firestore.
You must create a vector index on the associated field before you can perform nearest-neighbor
search.

## Parameters

| Parameter | Type | Description |
| :------ | :------ | :------ |
| `config` | `object` | - |
| `config.collection` | `string` | The name of the collection from which to query. |
| `config.contentField` | `string` \| (`snap`: `QueryDocumentSnapshot`\<`DocumentData`, `DocumentData`\>) => (\{ `"media"`: `undefined`; `"text"`: `string`; \} \| \{ `"media"`: \{ `"contentType"`: `string`; `"url"`: `string`; \}; `"text"`: `undefined`; \})[] | The name of the field containing the document content you wish to return. |
| `config.distanceMeasure`? | `"EUCLIDEAN"` \| `"COSINE"` \| `"DOT_PRODUCT"` | The distance measure to use when comparing vectors. Defaults to 'COSINE'. |
| `config.embedder` | `EmbedderArgument`\<`ZodTypeAny`\> | The embedder to use with this retriever. |
| `config.firestore` | `Firestore` | The Firestore database instance from which to query. |
| `config.label`? | `string` | Optional label for display in Developer UI. |
| `config.metadataFields`? | `string`[] \| (`snap`: `QueryDocumentSnapshot`\<`DocumentData`, `DocumentData`\>) => `Record`\<`string`, `any`\> | A list of fields to include in the returned document metadata. If not supplied, all fields other<br />than the vector are included. Alternatively, provide a transform function to extract the desired<br />metadata fields from a snapshot. |
| `config.name` | `string` | The name of the retriever. |
| `config.vectorField` | `string` | The name of the field within the collection containing the vector data. |

## Returns

`RetrieverAction`\<`ZodObject`\<\{
  `"limit"`: `ZodNumber`;
  `"where"`: `ZodOptional`\<`ZodRecord`\<`ZodString`, `ZodAny`\>\>;
 \}, `"strip"`, `ZodTypeAny`, \{
  `"limit"`: `number`;
  `"where"`: `Record`\<`string`, `any`\>;
 \}, \{
  `"limit"`: `number`;
  `"where"`: `Record`\<`string`, `any`\>;
 \}\>\>

## Source

[plugins/firebase/src/firestoreRetriever.ts:73](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/firebase/src/firestoreRetriever.ts#L73)
