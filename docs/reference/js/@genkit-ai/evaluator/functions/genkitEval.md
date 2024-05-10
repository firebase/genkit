# Function: genkitEval()

```ts
function genkitEval<ModelCustomOptions, EmbedderCustomOptions>(params: PluginOptions<ModelCustomOptions, EmbedderCustomOptions>): PluginProvider
```

Genkit evaluation plugin that provides the RAG evaluators

## Type parameters

| Type parameter |
| :------ |
| `ModelCustomOptions` *extends* `ZodType`\<`any`, `any`, `any`, `ModelCustomOptions`\> |
| `EmbedderCustomOptions` *extends* `ZodType`\<`any`, `any`, `any`, `EmbedderCustomOptions`\> |

## Parameters

| Parameter | Type |
| :------ | :------ |
| `params` | [`PluginOptions`](../interfaces/PluginOptions.md)\<`ModelCustomOptions`, `EmbedderCustomOptions`\> |

## Returns

`PluginProvider`

## Source

[plugins/evaluators/src/index.ts:65](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/plugins/evaluators/src/index.ts#L65)
