# Type alias: StepsFunction()\<I, O, S\>

```ts
type StepsFunction<I, O, S>: (input: z.infer<I>, streamingCallback: StreamingCallback<z.infer<S>> | undefined) => Promise<z.infer<O>>;
```

## Type parameters

| Type parameter | Value |
| :------ | :------ |
| `I` *extends* `z.ZodTypeAny` | `z.ZodTypeAny` |
| `O` *extends* `z.ZodTypeAny` | `z.ZodTypeAny` |
| `S` *extends* `z.ZodTypeAny` | `z.ZodTypeAny` |

## Parameters

| Parameter | Type |
| :------ | :------ |
| `input` | `z.infer`\<`I`\> |
| `streamingCallback` | `StreamingCallback`\<`z.infer`\<`S`\>\> \| `undefined` |

## Returns

`Promise`\<`z.infer`\<`O`\>\>

## Source

[flow/src/flow.ts:789](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/flow/src/flow.ts#L789)
