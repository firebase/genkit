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

[ai/src/retriever.ts:79](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/ai/src/retriever.ts#L79)
