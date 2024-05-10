# Function: prompt()

```ts
function prompt<Variables>(name: string, options?: {
  "variant": string;
}): Promise<Dotprompt<Variables>>
```

## Type parameters

| Type parameter | Value |
| :------ | :------ |
| `Variables` | `unknown` |

## Parameters

| Parameter | Type |
| :------ | :------ |
| `name` | `string` |
| `options`? | `object` |
| `options.variant`? | `string` |

## Returns

`Promise`\<[`Dotprompt`](../classes/Dotprompt.md)\<`Variables`\>\>

## Source

[plugins/dotprompt/src/index.ts:46](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/dotprompt/src/index.ts#L46)
