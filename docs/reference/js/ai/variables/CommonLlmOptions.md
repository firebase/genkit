# Variable: CommonLlmOptions

```ts
const CommonLlmOptions: ZodObject<{
  "temperature": ZodOptional<ZodNumber>;
  "topK": ZodOptional<ZodNumber>;
  "topP": ZodOptional<ZodNumber>;
 }, "strip", ZodTypeAny, {
  "temperature": number;
  "topK": number;
  "topP": number;
 }, {
  "temperature": number;
  "topK": number;
  "topP": number;
}>;
```

## Type declaration

| Member | Type | Value |
| :------ | :------ | :------ |
| `temperature` | `ZodOptional`\<`ZodNumber`\> | ... |
| `topK` | `ZodOptional`\<`ZodNumber`\> | ... |
| `topP` | `ZodOptional`\<`ZodNumber`\> | ... |

## Source

[ai/src/types.ts:85](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/ai/src/types.ts#L85)
