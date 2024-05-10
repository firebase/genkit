# Variable: imagen2

```ts
const imagen2: ModelReference<ZodObject<{
  "aspectRatio": ZodOptional<ZodEnum<["1:1", "9:16", "16:9"]>>;
  "language": ZodOptional<ZodEnum<["auto", "en", "es", "hi", "ja", "ko", "pt", "zh-TW", "zh", "zh-CN"]>>;
  "maxOutputTokens": ZodOptional<ZodNumber>;
  "negativePrompt": ZodOptional<ZodString>;
  "seed": ZodOptional<ZodNumber>;
  "stopSequences": ZodOptional<ZodArray<ZodString, "many">>;
  "temperature": ZodOptional<ZodNumber>;
  "topK": ZodOptional<ZodNumber>;
  "topP": ZodOptional<ZodNumber>;
  "version": ZodOptional<ZodString>;
 }, "strip", ZodTypeAny, {
  "aspectRatio": "1:1" | "9:16" | "16:9";
  "language":   | "auto"
     | "en"
     | "es"
     | "hi"
     | "ja"
     | "ko"
     | "pt"
     | "zh-TW"
     | "zh"
     | "zh-CN";
  "maxOutputTokens": number;
  "negativePrompt": string;
  "seed": number;
  "stopSequences": string[];
  "temperature": number;
  "topK": number;
  "topP": number;
  "version": string;
 }, {
  "aspectRatio": "1:1" | "9:16" | "16:9";
  "language":   | "auto"
     | "en"
     | "es"
     | "hi"
     | "ja"
     | "ko"
     | "pt"
     | "zh-TW"
     | "zh"
     | "zh-CN";
  "maxOutputTokens": number;
  "negativePrompt": string;
  "seed": number;
  "stopSequences": string[];
  "temperature": number;
  "topK": number;
  "topP": number;
  "version": string;
}>>;
```

## Source

[plugins/vertexai/src/imagen.ts:44](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/vertexai/src/imagen.ts#L44)
