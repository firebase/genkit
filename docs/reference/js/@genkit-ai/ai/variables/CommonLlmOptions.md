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

[ai/src/types.ts:85](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/ai/src/types.ts#L85)
