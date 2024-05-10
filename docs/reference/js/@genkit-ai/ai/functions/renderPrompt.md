# Function: renderPrompt()

```ts
function renderPrompt<I, CustomOptions>(params: {
  "config": TypeOf<CustomOptions>;
  "context": {
     "content": ({
        "media": undefined;
        "text": string;
       } | {
        "media": {
           "contentType": string;
           "url": string;
          };
        "text": undefined;
       })[];
     "metadata": Record<string, any>;
    }[];
  "input": TypeOf<I>;
  "model": ModelArgument<CustomOptions>;
  "prompt": PromptArgument<I>;
}): Promise<GenerateOptions>
```

## Type parameters

| Type parameter | Value |
| :------ | :------ |
| `I` *extends* `ZodType`\<`any`, `any`, `any`, `I`\> | `ZodTypeAny` |
| `CustomOptions` *extends* `ZodType`\<`any`, `any`, `any`, `CustomOptions`\> | `ZodTypeAny` |

## Parameters

| Parameter | Type |
| :------ | :------ |
| `params` | `object` |
| `params.config`? | `TypeOf`\<`CustomOptions`\> |
| `params.context`? | \{ `"content"`: (\{ `"media"`: `undefined`; `"text"`: `string`; \} \| \{ `"media"`: \{ `"contentType"`: `string`; `"url"`: `string`; \}; `"text"`: `undefined`; \})[]; `"metadata"`: `Record`\<`string`, `any`\>; \}[] |
| `params.input` | `TypeOf`\<`I`\> |
| `params.model` | `ModelArgument`\<`CustomOptions`\> |
| `params.prompt` | `PromptArgument`\<`I`\> |

## Returns

`Promise`\<[`GenerateOptions`](../interfaces/GenerateOptions.md)\>

## Source

[ai/src/prompt.ts:88](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/ai/src/prompt.ts#L88)
