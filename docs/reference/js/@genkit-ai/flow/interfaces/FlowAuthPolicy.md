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

[flow/src/flow.ts:92](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/flow/src/flow.ts#L92)
