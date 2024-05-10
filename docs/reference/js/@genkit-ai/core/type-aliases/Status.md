# Type alias: Status

```ts
type Status: {
  "code": StatusCodesSchema;
  "details": any;
  "message": string;
};
```

## Type declaration

| Member | Type | Value |
| :------ | :------ | :------ |
| `code` | [`StatusCodes`](../enumerations/StatusCodes.md) | StatusCodesSchema |
| `details` | `any` | ... |
| `message` | `string` | ... |

## Source

[core/src/statusTypes.ts:205](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/core/src/statusTypes.ts#L205)
