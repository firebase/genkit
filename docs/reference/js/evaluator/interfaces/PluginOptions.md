# Interface: PluginOptions\<ModelCustomOptions, EmbedderCustomOptions\>

## Type parameters

| Type parameter |
| :------ |
| `ModelCustomOptions` *extends* `z.ZodTypeAny` |
| `EmbedderCustomOptions` *extends* `z.ZodTypeAny` |

## Properties

| Property | Type |
| :------ | :------ |
| `embedder?` | `EmbedderReference`\<`EmbedderCustomOptions`\> |
| `embedderOptions?` | `TypeOf`\<`EmbedderCustomOptions`\> |
| `judge` | `ModelReference`\<`ModelCustomOptions`\> |
| `judgeConfig?` | `TypeOf`\<`ModelCustomOptions`\> |
| `metrics?` | [`GenkitMetric`](../enumerations/GenkitMetric.md)[] |
