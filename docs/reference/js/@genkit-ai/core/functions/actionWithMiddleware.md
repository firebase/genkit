# Function: actionWithMiddleware()

```ts
function actionWithMiddleware<I, O, M>(action: Action<I, O, M>, middleware: Middleware<TypeOf<I>, TypeOf<O>>[]): Action<I, O, M>
```

## Type parameters

| Type parameter | Value |
| :------ | :------ |
| `I` *extends* `ZodType`\<`any`, `any`, `any`, `I`\> | - |
| `O` *extends* `ZodType`\<`any`, `any`, `any`, `O`\> | - |
| `M` *extends* `Record`\<`string`, `any`\> | `Record`\<`string`, `any`\> |

## Parameters

| Parameter | Type |
| :------ | :------ |
| `action` | [`Action`](../type-aliases/Action.md)\<`I`, `O`, `M`\> |
| `middleware` | [`Middleware`](../interfaces/Middleware.md)\<`TypeOf`\<`I`\>, `TypeOf`\<`O`\>\>[] |

## Returns

[`Action`](../type-aliases/Action.md)\<`I`, `O`, `M`\>

## Source

[core/src/action.ts:82](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/core/src/action.ts#L82)
