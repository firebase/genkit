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

[plugins/dotprompt/src/prompt.ts:198](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/plugins/dotprompt/src/prompt.ts#L198)
