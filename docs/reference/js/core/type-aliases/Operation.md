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

[core/src/flowTypes.ts:103](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/core/src/flowTypes.ts#L103)
