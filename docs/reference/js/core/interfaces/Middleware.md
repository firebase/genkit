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

[core/src/action.ts:79](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/core/src/action.ts#L79)
