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

[plugins/vertexai/src/embedder.ts:102](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/vertexai/src/embedder.ts#L102)
