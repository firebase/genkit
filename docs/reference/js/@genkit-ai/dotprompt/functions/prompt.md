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

[plugins/dotprompt/src/index.ts:46](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/plugins/dotprompt/src/index.ts#L46)
