# Function: runFlow()

```ts
function runFlow<I, O, S>(
   flow: Flow<I, O, S> | FlowWrapper<I, O, S>, 
   payload?: TypeOf<I>, 
   opts?: {
  "withLocalAuthContext": unknown;
}): Promise<z.infer<O>>
```

Runs the flow. If the flow does not get interrupted may return a completed (done=true) operation.

## Type parameters

| Type parameter | Value |
| :------ | :------ |
| `I` *extends* `ZodType`\<`any`, `any`, `any`, `I`\> | `ZodTypeAny` |
| `O` *extends* `ZodType`\<`any`, `any`, `any`, `O`\> | `ZodTypeAny` |
| `S` *extends* `ZodType`\<`any`, `any`, `any`, `S`\> | `ZodTypeAny` |

## Parameters

| Parameter | Type |
| :------ | :------ |
| `flow` | [`Flow`](../classes/Flow.md)\<`I`, `O`, `S`\> \| [`FlowWrapper`](../interfaces/FlowWrapper.md)\<`I`, `O`, `S`\> |
| `payload`? | `TypeOf`\<`I`\> |
| `opts`? | `object` |
| `opts.withLocalAuthContext`? | `unknown` |

## Returns

`Promise`\<`z.infer`\<`O`\>\>

## Source

[flow/src/flow.ts:643](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/flow/src/flow.ts#L643)
