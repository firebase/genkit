# Type alias: GenerateStreamOptions\<O, CustomOptions\>

```ts
type GenerateStreamOptions<O, CustomOptions>: Omit<GenerateOptions<O, CustomOptions>, "streamingCallback">;
```

## Type parameters

| Type parameter | Value |
| :------ | :------ |
| `O` *extends* `z.ZodTypeAny` | `z.ZodTypeAny` |
| `CustomOptions` *extends* `z.ZodTypeAny` | *typeof* `GenerationCommonConfigSchema` |

## Source

[ai/src/generate.ts:677](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/ai/src/generate.ts#L677)
