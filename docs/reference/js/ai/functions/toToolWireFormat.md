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

[ai/src/types.ts:62](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/ai/src/types.ts#L62)
