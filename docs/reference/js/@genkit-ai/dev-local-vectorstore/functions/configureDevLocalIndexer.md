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

[plugins/dev-local-vectorstore/src/index.ts:206](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/plugins/dev-local-vectorstore/src/index.ts#L206)
