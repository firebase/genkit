# Function: langchain()

```ts
function langchain(...args: [LangchainPluginParams<ZodObject<{
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
 }>>]): PluginProvider
```

## Parameters

| Parameter | Type |
| :------ | :------ |
| ...`args` | [`LangchainPluginParams`\<`ZodObject`\<\{ `"maxOutputTokens"`: `ZodOptional`\<`ZodNumber`\>; `"stopSequences"`: `ZodOptional`\<`ZodArray`\<`ZodString`, `"many"`\>\>; `"temperature"`: `ZodOptional`\<`ZodNumber`\>; `"topK"`: `ZodOptional`\<`ZodNumber`\>; `"topP"`: `ZodOptional`\<`ZodNumber`\>; `"version"`: `ZodOptional`\<`ZodString`\>; \}, `"strip"`, `ZodTypeAny`, \{ `"maxOutputTokens"`: `number`; `"stopSequences"`: `string`[]; `"temperature"`: `number`; `"topK"`: `number`; `"topP"`: `number`; `"version"`: `string`; \}, \{ `"maxOutputTokens"`: `number`; `"stopSequences"`: `string`[]; `"temperature"`: `number`; `"topK"`: `number`; `"topP"`: `number`; `"version"`: `string`; \}\>\>] |

## Returns

`PluginProvider`

## Source

[plugins/langchain/src/index.ts:40](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/plugins/langchain/src/index.ts#L40)
