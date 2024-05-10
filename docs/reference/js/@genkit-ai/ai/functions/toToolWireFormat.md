# Function: toToolWireFormat()

```ts
function toToolWireFormat(actions?: Action<any, any, Record<string, any>>[]): z.infer<typeof ToolSchema>[] | undefined
```

Converts actions to tool definition sent to model inputs.

## Parameters

| Parameter | Type |
| :------ | :------ |
| `actions`? | `Action`\<`any`, `any`, `Record`\<`string`, `any`\>\>[] |

## Returns

`z.infer`\<*typeof* [`ToolSchema`](../variables/ToolSchema.md)\>[] \| `undefined`

## Source

[ai/src/types.ts:62](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/ai/src/types.ts#L62)
