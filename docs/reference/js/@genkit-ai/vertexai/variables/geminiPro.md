# Variable: geminiPro

```ts
const geminiPro: ModelReference<ZodObject<{
  "maxOutputTokens": ZodOptional<ZodNumber>;
  "safetySettings": ZodOptional<ZodArray<ZodObject<{
     "category": ZodNativeEnum<typeof HarmCategory>;
     "threshold": ZodNativeEnum<typeof HarmBlockThreshold>;
    }, "strip", ZodTypeAny, {
     "category": HarmCategory;
     "threshold": HarmBlockThreshold;
    }, {
     "category": HarmCategory;
     "threshold": HarmBlockThreshold;
    }>, "many">>;
  "stopSequences": ZodOptional<ZodArray<ZodString, "many">>;
  "temperature": ZodOptional<ZodNumber>;
  "topK": ZodOptional<ZodNumber>;
  "topP": ZodOptional<ZodNumber>;
  "version": ZodOptional<ZodString>;
 }, "strip", ZodTypeAny, {
  "maxOutputTokens": number;
  "safetySettings": {
     "category": HarmCategory;
     "threshold": HarmBlockThreshold;
    }[];
  "stopSequences": string[];
  "temperature": number;
  "topK": number;
  "topP": number;
  "version": string;
 }, {
  "maxOutputTokens": number;
  "safetySettings": {
     "category": HarmCategory;
     "threshold": HarmBlockThreshold;
    }[];
  "stopSequences": string[];
  "temperature": number;
  "topK": number;
  "topP": number;
  "version": string;
}>>;
```

## Source

[plugins/vertexai/src/gemini.ts:60](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/plugins/vertexai/src/gemini.ts#L60)
