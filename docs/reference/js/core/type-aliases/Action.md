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

[core/src/action.ts:48](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/core/src/action.ts#L48)
