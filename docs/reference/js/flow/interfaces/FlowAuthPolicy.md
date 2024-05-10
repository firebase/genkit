# Interface: FlowAuthPolicy()\<I\>

Flow Auth policy. Consumes the authorization context of the flow and
performs checks before the flow runs. If this throws, the flow will not
be executed.

## Type parameters

| Type parameter | Value |
| :------ | :------ |
| `I` *extends* `z.ZodTypeAny` | `z.ZodTypeAny` |

```ts
interface FlowAuthPolicy(auth: any, input: TypeOf<I>): void | Promise<void>
```

## Parameters

| Parameter | Type |
| :------ | :------ |
| `auth` | `any` |
| `input` | `TypeOf`\<`I`\> |

## Returns

`void` \| `Promise`\<`void`\>

## Source

[flow/src/flow.ts:92](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/flow/src/flow.ts#L92)
