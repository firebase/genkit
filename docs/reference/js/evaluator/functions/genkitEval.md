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

[plugins/evaluators/src/index.ts:65](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/evaluators/src/index.ts#L65)
