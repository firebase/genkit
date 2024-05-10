# Variable: geminiProVision

```ts
const geminiProVision: ModelReference<ZodObject<{
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

[plugins/vertexai/src/gemini.ts:75](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/vertexai/src/gemini.ts#L75)
