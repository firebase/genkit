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

[flow/src/flow.ts:789](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/flow/src/flow.ts#L789)
