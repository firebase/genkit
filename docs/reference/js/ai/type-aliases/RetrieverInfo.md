# Type alias: RetrieverInfo

```ts
type RetrieverInfo: {
  "label": string;
  "supports": {
     "media": boolean;
    };
};
```

## Type declaration

| Member | Type | Value | Description |
| :------ | :------ | :------ | :------ |
| `label` | `string` | ... | - |
| `supports` | \{
  `"media"`: `boolean`;
 \} | ... | Supported model capabilities. |
| `supports.media` | `boolean` | ... | Model can process media as part of the prompt (multimodal input). |

## Source

[ai/src/retriever.ts:68](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/ai/src/retriever.ts#L68)
