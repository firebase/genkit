# Type alias: LlmResponse

```ts
type LlmResponse: {
  "completion": string;
  "stats": LlmStatsSchema;
  "toolCalls": {
     "arguments": any;
     "toolName": string;
    }[];
};
```

## Type declaration

| Member | Type | Value |
| :------ | :------ | :------ |
| `completion` | `string` | ... |
| `stats` | \{
  `"inputTokenCount"`: `number`;
  `"latencyMs"`: `number`;
  `"outputTokenCount"`: `number`;
 \} | LlmStatsSchema |
| `stats.inputTokenCount` | `number` | ... |
| `stats.latencyMs` | `number` | ... |
| `stats.outputTokenCount` | `number` | ... |
| `toolCalls` | \{
  `"arguments"`: `any`;
  `"toolName"`: `string`;
 \}[] | ... |

## Source

[ai/src/types.ts:57](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/ai/src/types.ts#L57)
