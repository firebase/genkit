# Function: runWithStreamingCallback()

```ts
function runWithStreamingCallback<S, O>(streamingCallback: undefined | StreamingCallback<S>, fn: () => O): O
```

Executes provided function with streaming callback in async local storage which can be retrieved
using [getStreamingCallback](getStreamingCallback.md).

## Type parameters

| Type parameter |
| :------ |
| `S` |
| `O` |

## Parameters

| Parameter | Type |
| :------ | :------ |
| `streamingCallback` | `undefined` \| [`StreamingCallback`](../type-aliases/StreamingCallback.md)\<`S`\> |
| `fn` | () => `O` |

## Returns

`O`

## Source

[core/src/action.ts:238](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/core/src/action.ts#L238)
