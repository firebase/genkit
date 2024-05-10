# Function: devLocalVectorstore()

```ts
function devLocalVectorstore<EmbedderCustomOptions>(params: Params<EmbedderCustomOptions>[]): PluginProvider
```

Local file-based vectorstore plugin that provides retriever and indexer.

NOT INTENDED FOR USE IN PRODUCTION

## Type parameters

| Type parameter |
| :------ |
| `EmbedderCustomOptions` *extends* `ZodType`\<`any`, `any`, `any`, `EmbedderCustomOptions`\> |

## Parameters

| Parameter | Type |
| :------ | :------ |
| `params` | `Params`\<`EmbedderCustomOptions`\>[] |

## Returns

`PluginProvider`

## Source

[plugins/dev-local-vectorstore/src/index.ts:74](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/plugins/dev-local-vectorstore/src/index.ts#L74)
