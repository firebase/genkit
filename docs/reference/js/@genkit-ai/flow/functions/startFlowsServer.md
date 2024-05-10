# Function: startFlowsServer()

```ts
function startFlowsServer(params?: {
  "cors": CorsOptions;
  "flows": Flow<any, any, any>[];
  "port": number;
 }): void
```

## Parameters

| Parameter | Type |
| :------ | :------ |
| `params`? | `object` |
| `params.cors`? | `CorsOptions` |
| `params.flows`? | [`Flow`](../classes/Flow.md)\<`any`, `any`, `any`\>[] |
| `params.port`? | `number` |

## Returns

`void`

## Source

[flow/src/flow.ts:834](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/flow/src/flow.ts#L834)
