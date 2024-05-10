# Type alias: Plugin()\<T\>

```ts
type Plugin<T>: (...args: T) => PluginProvider;
```

## Type parameters

| Type parameter |
| :------ |
| `T` *extends* `any`[] |

## Parameters

| Parameter | Type |
| :------ | :------ |
| ...`args` | `T` |

## Returns

[`PluginProvider`](../interfaces/PluginProvider.md)

## Source

[core/src/plugin.ts:54](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/core/src/plugin.ts#L54)
