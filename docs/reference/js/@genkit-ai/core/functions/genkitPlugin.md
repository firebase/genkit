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

[core/src/plugin.ts:59](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/core/src/plugin.ts#L59)
