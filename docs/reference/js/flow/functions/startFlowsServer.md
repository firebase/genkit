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

[flow/src/flow.ts:834](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/flow/src/flow.ts#L834)
