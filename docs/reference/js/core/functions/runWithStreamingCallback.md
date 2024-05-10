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

[core/src/action.ts:238](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/core/src/action.ts#L238)
