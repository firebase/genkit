# Interface: Middleware()\<I, O\>

## Type parameters

| Type parameter | Value |
| :------ | :------ |
| `I` | `any` |
| `O` | `any` |

```ts
interface Middleware(req: I, next: (req?: I) => Promise<O>): Promise<O>
```

## Parameters

| Parameter | Type |
| :------ | :------ |
| `req` | `I` |
| `next` | (`req`?: `I`) => `Promise`\<`O`\> |

## Returns

`Promise`\<`O`\>

## Source

[core/src/action.ts:79](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/core/src/action.ts#L79)
