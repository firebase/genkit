# Interface: FlowStateStore

Flow state store persistence interface.

## Methods

### list()

```ts
list(query?: FlowStateQuery): Promise<FlowStateQueryResponse>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `query`? | [`FlowStateQuery`](FlowStateQuery.md) |

#### Returns

`Promise`\<[`FlowStateQueryResponse`](FlowStateQueryResponse.md)\>

#### Source

[core/src/flowTypes.ts:38](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/core/src/flowTypes.ts#L38)

***

### load()

```ts
load(id: string): Promise<undefined | {
  "blockedOnStep": null | {
     "name": string;
     "schema": string;
    };
  "cache": Record<string, {
     "empty": true;
     "value": any;
    }>;
  "eventsTriggered": Record<string, any>;
  "executions": {
     "endTime": number;
     "startTime": number;
     "traceIds": string[];
    }[];
  "flowId": string;
  "input": unknown;
  "name": string;
  "operation": OperationSchema;
  "startTime": number;
  "traceContext": string;
}>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `id` | `string` |

#### Returns

`Promise`\<`undefined` \| \{
  `"blockedOnStep"`: `null` \| \{
     `"name"`: `string`;
     `"schema"`: `string`;
    \};
  `"cache"`: `Record`\<`string`, \{
     `"empty"`: `true`;
     `"value"`: `any`;
    \}\>;
  `"eventsTriggered"`: `Record`\<`string`, `any`\>;
  `"executions"`: \{
     `"endTime"`: `number`;
     `"startTime"`: `number`;
     `"traceIds"`: `string`[];
    \}[];
  `"flowId"`: `string`;
  `"input"`: `unknown`;
  `"name"`: `string`;
  `"operation"`: `OperationSchema`;
  `"startTime"`: `number`;
  `"traceContext"`: `string`;
 \}\>

#### Source

[core/src/flowTypes.ts:37](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/core/src/flowTypes.ts#L37)

***

### save()

```ts
save(id: string, state: {
  "blockedOnStep": null | {
     "name": string;
     "schema": string;
    };
  "cache": Record<string, {
     "empty": true;
     "value": any;
    }>;
  "eventsTriggered": Record<string, any>;
  "executions": {
     "endTime": number;
     "startTime": number;
     "traceIds": string[];
    }[];
  "flowId": string;
  "input": unknown;
  "name": string;
  "operation": OperationSchema;
  "startTime": number;
  "traceContext": string;
}): Promise<void>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `id` | `string` |
| `state` | `object` |
| `state.blockedOnStep` | `null` \| \{ `"name"`: `string`; `"schema"`: `string`; \} |
| `state.cache` | `Record`\<`string`, \{ `"empty"`: `true`; `"value"`: `any`; \}\> |
| `state.eventsTriggered` | `Record`\<`string`, `any`\> |
| `state.executions` | \{ `"endTime"`: `number`; `"startTime"`: `number`; `"traceIds"`: `string`[]; \}[] |
| `state.flowId` | `string` |
| `state.input`? | `unknown` |
| `state.name`? | `string` |
| `state.operation` | `object` |
| `state.operation.blockedOnStep`? | `object` |
| `state.operation.blockedOnStep.name` | `string` |
| `state.operation.blockedOnStep.schema`? | `string` |
| `state.operation.done` | `boolean` |
| `state.operation.metadata`? | `any` |
| `state.operation.name` | `string` |
| `state.operation.result`? | \{ `"response"`: `unknown`; \} & \{ `"error"`: `string`; `"stacktrace"`: `string`; \} |
| `state.startTime` | `number` |
| `state.traceContext`? | `string` |

#### Returns

`Promise`\<`void`\>

#### Source

[core/src/flowTypes.ts:36](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/core/src/flowTypes.ts#L36)
