# Type alias: Action\<I, O, M\>

```ts
type Action<I, O, M>: (input: z.infer<I>) => Promise<z.infer<O>> & {
  "__action": ActionMetadata<I, O, M>;
};
```

## Type declaration

| Member | Type |
| :------ | :------ |
| `__action` | [`ActionMetadata`](../interfaces/ActionMetadata.md)\<`I`, `O`, `M`\> |

## Type parameters

| Type parameter | Value |
| :------ | :------ |
| `I` *extends* `z.ZodTypeAny` | `z.ZodTypeAny` |
| `O` *extends* `z.ZodTypeAny` | `z.ZodTypeAny` |
| `M` *extends* `Record`\<`string`, `any`\> | `Record`\<`string`, `any`\> |

## Source

[core/src/action.ts:48](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/core/src/action.ts#L48)
