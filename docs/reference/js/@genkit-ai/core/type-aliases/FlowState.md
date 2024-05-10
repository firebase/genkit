# Type alias: FlowState

```ts
type FlowState: {
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
};
```

## Type declaration

| Member | Type | Value |
| :------ | :------ | :------ |
| `blockedOnStep` | `null` \| \{
  `"name"`: `string`;
  `"schema"`: `string`;
 \} | ... |
| `cache` | `Record`\<`string`, \{
  `"empty"`: `true`;
  `"value"`: `any`;
 \}\> | ... |
| `eventsTriggered` | `Record`\<`string`, `any`\> | ... |
| `executions` | \{
  `"endTime"`: `number`;
  `"startTime"`: `number`;
  `"traceIds"`: `string`[];
 \}[] | ... |
| `flowId` | `string` | ... |
| `input` | `unknown` | ... |
| `name` | `string` | ... |
| `operation` | \{
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
 \} | OperationSchema |
| `operation.blockedOnStep` | \{
  `"name"`: `string`;
  `"schema"`: `string`;
 \} | ... |
| `operation.blockedOnStep.name` | `string` | ... |
| `operation.blockedOnStep.schema` | `string` | ... |
| `operation.done` | `boolean` | ... |
| `operation.metadata` | `any` | ... |
| `operation.name` | `string` | ... |
| `operation.result` | \{
  `"response"`: `unknown`;
 \} & \{
  `"error"`: `string`;
  `"stacktrace"`: `string`;
 \} | ... |
| `startTime` | `number` | ... |
| `traceContext` | `string` | ... |

## Source

[core/src/flowTypes.ts:133](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/core/src/flowTypes.ts#L133)
