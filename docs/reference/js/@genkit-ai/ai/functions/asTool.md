# Function: asTool()

```ts
function asTool<I, O>(action: Action<I, O, Record<string, any>>): ToolAction<I, O>
```

## Type parameters

| Type parameter |
| :------ |
| `I` *extends* `ZodType`\<`any`, `any`, `any`, `I`\> |
| `O` *extends* `ZodType`\<`any`, `any`, `any`, `O`\> |

## Parameters

| Parameter | Type |
| :------ | :------ |
| `action` | `Action`\<`I`, `O`, `Record`\<`string`, `any`\>\> |

## Returns

[`ToolAction`](../type-aliases/ToolAction.md)\<`I`, `O`\>

## Source

[ai/src/tool.ts:40](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/ai/src/tool.ts#L40)
