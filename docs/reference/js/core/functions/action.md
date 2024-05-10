# Function: action()

```ts
function action<I, O, M>(config: ActionParams<I, O, M>, fn: (input: TypeOf<I>) => Promise<TypeOf<O>>): Action<I, O>
```

Creates an action with the provided config.

## Type parameters

| Type parameter | Value |
| :------ | :------ |
| `I` *extends* `ZodType`\<`any`, `any`, `any`, `I`\> | - |
| `O` *extends* `ZodType`\<`any`, `any`, `any`, `O`\> | - |
| `M` *extends* `Record`\<`string`, `any`\> | `Record`\<`string`, `any`\> |

## Parameters

| Parameter | Type |
| :------ | :------ |
| `config` | `ActionParams`\<`I`, `O`, `M`\> |
| `fn` | (`input`: `TypeOf`\<`I`\>) => `Promise`\<`TypeOf`\<`O`\>\> |

## Returns

[`Action`](../type-aliases/Action.md)\<`I`, `O`\>

## Source

[core/src/action.ts:112](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/core/src/action.ts#L112)
