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

[ai/src/prompt.ts:32](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/ai/src/prompt.ts#L32)
