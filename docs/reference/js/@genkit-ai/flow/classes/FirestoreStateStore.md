# Class: FirestoreStateStore

Implementation of flow state store that persistes flow state in Firestore.

## Implements

- [`FlowStateStore`](../interfaces/FlowStateStore.md)

## Constructors

### new FirestoreStateStore()

```ts
new FirestoreStateStore(params: {
  "collection": string;
  "databaseId": string;
  "projectId": string;
 }): FirestoreStateStore
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `params` | `object` |
| `params.collection`? | `string` |
| `params.databaseId`? | `string` |
| `params.projectId`? | `string` |

#### Returns

[`FirestoreStateStore`](FirestoreStateStore.md)

#### Source

[flow/src/firestoreStateStore.ts:35](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/flow/src/firestoreStateStore.ts#L35)

## Properties

| Property | Modifier | Type |
| :------ | :------ | :------ |
| `collection` | `readonly` | `string` |
| `databaseId` | `readonly` | `string` |
| `db` | `readonly` | `Firestore` |

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

#### Implementation of

[`FlowStateStore`](../interfaces/FlowStateStore.md).[`list`](../interfaces/FlowStateStore.md#list)

#### Source

[flow/src/firestoreStateStore.ts:65](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/flow/src/firestoreStateStore.ts#L65)

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

#### Implementation of

[`FlowStateStore`](../interfaces/FlowStateStore.md).[`load`](../interfaces/FlowStateStore.md#load)

#### Source

[flow/src/firestoreStateStore.ts:50](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/flow/src/firestoreStateStore.ts#L50)

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

#### Implementation of

[`FlowStateStore`](../interfaces/FlowStateStore.md).[`save`](../interfaces/FlowStateStore.md#save)

#### Source

[flow/src/firestoreStateStore.ts:60](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/flow/src/firestoreStateStore.ts#L60)
