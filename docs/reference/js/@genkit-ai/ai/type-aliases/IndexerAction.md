# Type alias: IndexerAction\<IndexerOptions\>

```ts
type IndexerAction<IndexerOptions>: Action<typeof IndexerRequestSchema, z.ZodVoid> & {
  "__configSchema": IndexerOptions;
};
```

## Type declaration

| Member | Type |
| :------ | :------ |
| `__configSchema` | `IndexerOptions` |

## Type parameters

| Type parameter | Value |
| :------ | :------ |
| `IndexerOptions` *extends* `z.ZodTypeAny` | `z.ZodTypeAny` |

## Source

[ai/src/retriever.ts:79](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/ai/src/retriever.ts#L79)
