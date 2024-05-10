# Type alias: FlowInvokeEnvelopeMessage

```ts
type FlowInvokeEnvelopeMessage: {
  "resume": {
     "flowId": string;
     "payload": unknown;
    };
  "retry": {
     "flowId": string;
    };
  "runScheduled": {
     "flowId": string;
    };
  "schedule": {
     "delay": number;
     "input": unknown;
    };
  "start": {
     "input": unknown;
     "labels": Record<string, string>;
    };
  "state": {
     "flowId": string;
    };
};
```

## Type declaration

| Member | Type | Value |
| :------ | :------ | :------ |
| `resume` | \{
  `"flowId"`: `string`;
  `"payload"`: `unknown`;
 \} | ... |
| `resume.flowId` | `string` | ... |
| `resume.payload` | `unknown` | ... |
| `retry` | \{
  `"flowId"`: `string`;
 \} | ... |
| `retry.flowId` | `string` | ... |
| `runScheduled` | \{
  `"flowId"`: `string`;
 \} | ... |
| `runScheduled.flowId` | `string` | ... |
| `schedule` | \{
  `"delay"`: `number`;
  `"input"`: `unknown`;
 \} | ... |
| `schedule.delay` | `number` | ... |
| `schedule.input` | `unknown` | ... |
| `start` | \{
  `"input"`: `unknown`;
  `"labels"`: `Record`\<`string`, `string`\>;
 \} | ... |
| `start.input` | `unknown` | ... |
| `start.labels` | `Record`\<`string`, `string`\> | ... |
| `state` | \{
  `"flowId"`: `string`;
 \} | ... |
| `state.flowId` | `string` | ... |

## Source

[flow/src/types.ts:85](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/flow/src/types.ts#L85)
