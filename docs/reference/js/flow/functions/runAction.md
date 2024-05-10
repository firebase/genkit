# Function: runAction()

```ts
function runAction<I, O>(action: Action<I, O, Record<string, any>>, input: TypeOf<I>): Promise<z.infer<O>>
```

A flow steap that executes an action with provided input and memoizes the output.

## Type parameters

| Type parameter |
| :------ |
| `I` *extends* `ZodType`\<`any`, `any`, `any`, `I`\> |
| `O` *extends* `ZodType`\<`any`, `any`, `any`, `O`\> |

## Parameters

| Parameter | Type |
| :------ | :------ |
| `action` | `Action`\<`I`, `O`, `Record`\<`string`, `any`\>\> |
| `input` | `TypeOf`\<`I`\> |

## Returns

`Promise`\<`z.infer`\<`O`\>\>

## Source

[flow/src/steps.ts:24](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/flow/src/steps.ts#L24)
