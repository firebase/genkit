# Variable: textEmbeddingGecko

```ts
const textEmbeddingGecko: EmbedderReference<ZodObject<{
  "taskType": ZodOptional<ZodEnum<["RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY", "SEMANTIC_SIMILARITY", "CLASSIFICATION", "CLUSTERING"]>>;
  "title": ZodOptional<ZodString>;
 }, "strip", ZodTypeAny, {
  "taskType":   | "RETRIEVAL_DOCUMENT"
     | "RETRIEVAL_QUERY"
     | "SEMANTIC_SIMILARITY"
     | "CLASSIFICATION"
     | "CLUSTERING";
  "title": string;
 }, {
  "taskType":   | "RETRIEVAL_DOCUMENT"
     | "RETRIEVAL_QUERY"
     | "SEMANTIC_SIMILARITY"
     | "CLASSIFICATION"
     | "CLUSTERING";
  "title": string;
 }>> = textEmbeddingGecko003;
```

## Source

[plugins/vertexai/src/embedder.ts:102](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/plugins/vertexai/src/embedder.ts#L102)
