# Function: runMap()

```ts
function runMap<I, O>(
   stepName: string, 
   input: I[], 
fn: (i: I) => Promise<O>): Promise<O[]>
```

A helper that takes an array of inputs and maps each input to a run step.

## Type parameters

| Type parameter |
| :------ |
| `I` |
| `O` |

## Parameters

| Parameter | Type |
| :------ | :------ |
| `stepName` | `string` |
| `input` | `I`[] |
| `fn` | (`i`: `I`) => `Promise`\<`O`\> |

## Returns

`Promise`\<`O`[]\>

## Source

[flow/src/steps.ts:59](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/flow/src/steps.ts#L59)
