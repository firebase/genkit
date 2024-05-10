# Interface: FlowStateQueryResponse

## Properties

| Property | Type |
| :------ | :------ |
| `continuationToken?` | `string` |
| `flowStates` | \{ `"blockedOnStep"`: `null` \| \{ `"name"`: `string`; `"schema"`: `string`; \}; `"cache"`: `Record`\<`string`, \{ `"empty"`: `true`; `"value"`: `any`; \}\>; `"eventsTriggered"`: `Record`\<`string`, `any`\>; `"executions"`: \{ `"endTime"`: `number`; `"startTime"`: `number`; `"traceIds"`: `string`[]; \}[]; `"flowId"`: `string`; `"input"`: `unknown`; `"name"`: `string`; `"operation"`: `OperationSchema`; `"startTime"`: `number`; `"traceContext"`: `string`; \}[] |
