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

[ai/src/tool.ts:40](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/ai/src/tool.ts#L40)
