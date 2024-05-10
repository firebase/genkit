# Function: configureDevLocalIndexer()

```ts
function configureDevLocalIndexer<EmbedderCustomOptions>(params: {
  "embedder": EmbedderArgument<EmbedderCustomOptions>;
  "embedderOptions": TypeOf<EmbedderCustomOptions>;
  "indexName": string;
}): IndexerAction<ZodTypeAny>
```

Configures a local vectorstore indexer.

## Type parameters

| Type parameter |
| :------ |
| `EmbedderCustomOptions` *extends* `ZodType`\<`any`, `any`, `any`, `EmbedderCustomOptions`\> |

## Parameters

| Parameter | Type |
| :------ | :------ |
| `params` | `object` |
| `params.embedder` | `EmbedderArgument`\<`EmbedderCustomOptions`\> |
| `params.embedderOptions`? | `TypeOf`\<`EmbedderCustomOptions`\> |
| `params.indexName` | `string` |

## Returns

`IndexerAction`\<`ZodTypeAny`\>

## Source

[plugins/dev-local-vectorstore/src/index.ts:206](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/dev-local-vectorstore/src/index.ts#L206)
