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

[plugins/dev-local-vectorstore/src/index.ts:74](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/dev-local-vectorstore/src/index.ts#L74)
