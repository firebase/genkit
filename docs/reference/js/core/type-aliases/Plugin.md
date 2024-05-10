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

[core/src/plugin.ts:54](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/core/src/plugin.ts#L54)
