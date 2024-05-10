# Function: generateStream()

```ts
function generateStream<O, CustomOptions>(options: GenerateOptions<O, CustomOptions> | PromiseLike<GenerateOptions<O, CustomOptions>>): Promise<GenerateStreamResponse<O>>
```

## Type parameters

| Type parameter | Value |
| :------ | :------ |
| `O` *extends* `ZodType`\<`any`, `any`, `any`, `O`\> | `ZodTypeAny` |
| `CustomOptions` *extends* `ZodType`\<`any`, `any`, `any`, `CustomOptions`\> | `ZodObject`\<\{
  `"maxOutputTokens"`: `ZodOptional`\<`ZodNumber`\>;
  `"stopSequences"`: `ZodOptional`\<`ZodArray`\<`ZodString`, `"many"`\>\>;
  `"temperature"`: `ZodOptional`\<`ZodNumber`\>;
  `"topK"`: `ZodOptional`\<`ZodNumber`\>;
  `"topP"`: `ZodOptional`\<`ZodNumber`\>;
  `"version"`: `ZodOptional`\<`ZodString`\>;
 \}, `"strip"`, `ZodTypeAny`, \{
  `"maxOutputTokens"`: `number`;
  `"stopSequences"`: `string`[];
  `"temperature"`: `number`;
  `"topK"`: `number`;
  `"topP"`: `number`;
  `"version"`: `string`;
 \}, \{
  `"maxOutputTokens"`: `number`;
  `"stopSequences"`: `string`[];
  `"temperature"`: `number`;
  `"topK"`: `number`;
  `"topP"`: `number`;
  `"version"`: `string`;
 \}\> |

## Parameters

| Parameter | Type |
| :------ | :------ |
| `options` | [`GenerateOptions`](../interfaces/GenerateOptions.md)\<`O`, `CustomOptions`\> \| `PromiseLike`\<[`GenerateOptions`](../interfaces/GenerateOptions.md)\<`O`, `CustomOptions`\>\> |

## Returns

`Promise`\<[`GenerateStreamResponse`](../interfaces/GenerateStreamResponse.md)\<`O`\>\>

## Source

[ai/src/generate.ts:697](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/ai/src/generate.ts#L697)
