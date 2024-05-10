# Function: defineAction()

```ts
function defineAction<I, O, M>(config: ActionParams<I, O, M> & {
  "actionType": ActionType;
}, fn: (input: TypeOf<I>) => Promise<TypeOf<O>>): Action<I, O>
```

Defines an action with the given config and registers it in the registry.

## Type parameters

| Type parameter | Value |
| :------ | :------ |
| `I` *extends* `ZodType`\<`any`, `any`, `any`, `I`\> | - |
| `O` *extends* `ZodType`\<`any`, `any`, `any`, `O`\> | - |
| `M` *extends* `Record`\<`string`, `any`\> | `Record`\<`string`, `any`\> |

## Parameters

| Parameter | Type |
| :------ | :------ |
| `config` | `ActionParams`\<`I`, `O`, `M`\> & \{ `"actionType"`: `ActionType`; \} |
| `fn` | (`input`: `TypeOf`\<`I`\>) => `Promise`\<`TypeOf`\<`O`\>\> |

## Returns

[`Action`](../type-aliases/Action.md)\<`I`, `O`\>

## Source

[core/src/action.ts:209](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/core/src/action.ts#L209)
