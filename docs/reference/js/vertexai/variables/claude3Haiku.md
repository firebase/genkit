# Variable: claude3Haiku

```ts
const claude3Haiku: ModelReference<ZodObject<{
  "maxOutputTokens": ZodOptional<ZodNumber>;
  "stopSequences": ZodOptional<ZodArray<ZodString, "many">>;
  "temperature": ZodOptional<ZodNumber>;
  "topK": ZodOptional<ZodNumber>;
  "topP": ZodOptional<ZodNumber>;
  "version": ZodOptional<ZodString>;
 }, "strip", ZodTypeAny, {
  "maxOutputTokens": number;
  "stopSequences": string[];
  "temperature": number;
  "topK": number;
  "topP": number;
  "version": string;
 }, {
  "maxOutputTokens": number;
  "stopSequences": string[];
  "temperature": number;
  "topK": number;
  "topP": number;
  "version": string;
}>>;
```

## Source

[plugins/vertexai/src/anthropic.ts:54](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/vertexai/src/anthropic.ts#L54)
