# Type alias: PromptAction\<I\>

```ts
type PromptAction<I>: Action<I, typeof GenerateRequestSchema> & {
  "__action": {
     "metadata": {
        "type": "prompt";
       };
    };
};
```

## Type declaration

| Member | Type |
| :------ | :------ |
| `__action` | \{
  `"metadata"`: \{
     `"type"`: `"prompt"`;
    \};
 \} |
| `__action.metadata` | \{
  `"type"`: `"prompt"`;
 \} |
| `__action.metadata.type` | `"prompt"` |

## Type parameters

| Type parameter | Value |
| :------ | :------ |
| `I` *extends* `z.ZodTypeAny` | `z.ZodTypeAny` |

## Source

[ai/src/prompt.ts:32](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/ai/src/prompt.ts#L32)
