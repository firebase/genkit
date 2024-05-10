# Type alias: ToolAction\<I, O\>

```ts
type ToolAction<I, O>: Action<I, O> & {
  "__action": {
     "metadata": {
        "type": "tool";
       };
    };
};
```

## Type declaration

| Member | Type |
| :------ | :------ |
| `__action` | \{
  `"metadata"`: \{
     `"type"`: `"tool"`;
    \};
 \} |
| `__action.metadata` | \{
  `"type"`: `"tool"`;
 \} |
| `__action.metadata.type` | `"tool"` |

## Type parameters

| Type parameter | Value |
| :------ | :------ |
| `I` *extends* `z.ZodTypeAny` | `z.ZodTypeAny` |
| `O` *extends* `z.ZodTypeAny` | `z.ZodTypeAny` |

## Source

[ai/src/tool.ts:24](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/ai/src/tool.ts#L24)
