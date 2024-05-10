# Function: genkitPlugin()

```ts
function genkitPlugin<T>(pluginName: string, initFn: T): Plugin<Parameters<T>>
```

Defines a Genkit plugin.

## Type parameters

| Type parameter |
| :------ |
| `T` *extends* `PluginInit` |

## Parameters

| Parameter | Type |
| :------ | :------ |
| `pluginName` | `string` |
| `initFn` | `T` |

## Returns

[`Plugin`](../type-aliases/Plugin.md)\<`Parameters`\<`T`\>\>

## Source

[core/src/plugin.ts:59](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/core/src/plugin.ts#L59)
