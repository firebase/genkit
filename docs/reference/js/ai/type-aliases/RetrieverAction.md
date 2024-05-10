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

[ai/src/retriever.ts:70](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/ai/src/retriever.ts#L70)
