# Type alias: Operation

```ts
type Operation: {
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
```

## Type declaration

| Member | Type | Value |
| :------ | :------ | :------ |
| `blockedOnStep` | \{
  `"name"`: `string`;
  `"schema"`: `string`;
 \} | ... |
| `blockedOnStep.name` | `string` | ... |
| `blockedOnStep.schema` | `string` | ... |
| `done` | `boolean` | ... |
| `metadata` | `any` | ... |
| `name` | `string` | ... |
| `result` | \{
  `"response"`: `unknown`;
 \} & \{
  `"error"`: `string`;
  `"stacktrace"`: `string`;
 \} | ... |

## Source

[core/src/flowTypes.ts:103](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/core/src/flowTypes.ts#L103)
