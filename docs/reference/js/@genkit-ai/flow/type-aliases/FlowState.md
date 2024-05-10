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
};
```

## Type declaration

| Member | Type |
| :------ | :------ |
| `blockedOnStep` | `null` \| \{
  `"name"`: `string`;
  `"schema"`: `string`;
 \} |
| `cache` | `Record`\<`string`, \{
  `"empty"`: `true`;
  `"value"`: `any`;
 \}\> |
| `eventsTriggered` | `Record`\<`string`, `any`\> |
| `executions` | \{
  `"endTime"`: `number`;
  `"startTime"`: `number`;
  `"traceIds"`: `string`[];
 \}[] |
| `flowId` | `string` |
| `input` | `unknown` |
| `name` | `string` |
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
 \} |
| `operation.blockedOnStep` | \{
  `"name"`: `string`;
  `"schema"`: `string`;
 \} |
| `operation.blockedOnStep.name` | `string` |
| `operation.blockedOnStep.schema` | `string` |
| `operation.done` | `boolean` |
| `operation.metadata` | `any` |
| `operation.name` | `string` |
| `operation.result` | \{
  `"response"`: `unknown`;
 \} & \{
  `"error"`: `string`;
  `"stacktrace"`: `string`;
 \} |
| `startTime` | `number` |
| `traceContext` | `string` |

## Source

core/lib/flowTypes.d.ts:321
