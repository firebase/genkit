# Function: generate()

```ts
function generate<O, CustomOptions>(options: GenerateOptions<O, CustomOptions> | PromiseLike<GenerateOptions<O, CustomOptions>>): Promise<GenerateResponse<z.infer<O>>>
```

Generate calls a generative model based on the provided prompt and configuration. If
`history` is provided, the generation will include a conversation history in its
request. If `tools` are provided, the generate method will automatically resolve
tool calls returned from the model unless `returnToolRequests` is set to `true`.

See `GenerateOptions` for detailed information about available options.

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

| Parameter | Type | Description |
| :------ | :------ | :------ |
| `options` | [`GenerateOptions`](../interfaces/GenerateOptions.md)\<`O`, `CustomOptions`\> \| `PromiseLike`\<[`GenerateOptions`](../interfaces/GenerateOptions.md)\<`O`, `CustomOptions`\>\> | The options for this generation request. |

## Returns

`Promise`\<[`GenerateResponse`](../classes/GenerateResponse.md)\<`z.infer`\<`O`\>\>\>

The generated response based on the provided parameters.

## Source

[ai/src/generate.ts:547](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/ai/src/generate.ts#L547)
