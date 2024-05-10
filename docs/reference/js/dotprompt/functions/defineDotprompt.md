# Function: defineDotprompt()

```ts
function defineDotprompt<V>(options: PromptMetadata<V, ZodTypeAny>, template: string): Dotprompt<z.infer<V>>
```

## Type parameters

| Type parameter | Value |
| :------ | :------ |
| `V` *extends* `ZodType`\<`any`, `any`, `any`, `V`\> | `ZodTypeAny` |

## Parameters

| Parameter | Type |
| :------ | :------ |
| `options` | `PromptMetadata`\<`V`, `ZodTypeAny`\> |
| `template` | `string` |

## Returns

[`Dotprompt`](../classes/Dotprompt.md)\<`z.infer`\<`V`\>\>

## Source

[plugins/dotprompt/src/prompt.ts:198](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/dotprompt/src/prompt.ts#L198)
