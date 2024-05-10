# Type alias: RetrieverAction\<CustomOptions\>

```ts
type RetrieverAction<CustomOptions>: Action<typeof RetrieverRequestSchema, typeof RetrieverResponseSchema, {
  "model": RetrieverInfo;
 }> & {
  "__configSchema": CustomOptions;
};
```

## Type declaration

| Member | Type |
| :------ | :------ |
| `__configSchema` | `CustomOptions` |

## Type parameters

| Type parameter | Value |
| :------ | :------ |
| `CustomOptions` *extends* `z.ZodTypeAny` | `z.ZodTypeAny` |

## Source

[ai/src/retriever.ts:70](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/ai/src/retriever.ts#L70)
