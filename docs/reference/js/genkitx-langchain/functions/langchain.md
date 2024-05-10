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

[plugins/langchain/src/index.ts:40](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/langchain/src/index.ts#L40)
