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

[core/src/statusTypes.ts:205](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/core/src/statusTypes.ts#L205)
