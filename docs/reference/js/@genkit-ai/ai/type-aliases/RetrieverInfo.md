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

[ai/src/retriever.ts:68](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/ai/src/retriever.ts#L68)
