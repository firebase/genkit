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

| Member | Type |
| :------ | :------ |
| `blockedOnStep` | \{
  `"name"`: `string`;
  `"schema"`: `string`;
 \} |
| `blockedOnStep.name` | `string` |
| `blockedOnStep.schema` | `string` |
| `done` | `boolean` |
| `metadata` | `any` |
| `name` | `string` |
| `result` | \{
  `"response"`: `unknown`;
 \} & \{
  `"error"`: `string`;
  `"stacktrace"`: `string`;
 \} |

## Source

core/lib/flowTypes.d.ts:146
