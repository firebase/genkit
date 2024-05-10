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
| `query`? | `FlowStateQuery` |

#### Returns

`Promise`\<`FlowStateQueryResponse`\>

#### Source

core/lib/flowTypes.d.ts:33

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
  "operation": {
     "blockedOnStep": {
        "name": string;
        "schema": string;
       };
     "done": boolean;
     "metadata": any;
     "name": string;
     "result": {
        "response": unknown;
       } & {
        "error": string;
        "stacktrace": string;
       };
    };
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
  `"operation"`: \{
     `"blockedOnStep"`: \{
        `"name"`: `string`;
        `"schema"`: `string`;
       \};
     `"done"`: `boolean`;
     `"metadata"`: `any`;
     `"name"`: `string`;
     `"result"`: \{
        `"response"`: `unknown`;
       \} & \{
        `"error"`: `string`;
        `"stacktrace"`: `string`;
       \};
    \};
  `"startTime"`: `number`;
  `"traceContext"`: `string`;
 \}\>

#### Source

core/lib/flowTypes.d.ts:32

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
  "operation": {
     "blockedOnStep": {
        "name": string;
        "schema": string;
       };
     "done": boolean;
     "metadata": any;
     "name": string;
     "result": {
        "response": unknown;
       } & {
        "error": string;
        "stacktrace": string;
       };
    };
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

core/lib/flowTypes.d.ts:31
