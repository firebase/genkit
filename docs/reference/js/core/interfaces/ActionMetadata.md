# Interface: ActionMetadata\<I, O, M\>

## Type parameters

| Type parameter | Value |
| :------ | :------ |
| `I` *extends* `z.ZodTypeAny` | - |
| `O` *extends* `z.ZodTypeAny` | - |
| `M` *extends* `Record`\<`string`, `any`\> | `Record`\<`string`, `any`\> |

## Properties

| Property | Type |
| :------ | :------ |
| `actionType?` | `ActionType` |
| `description?` | `string` |
| `inputJsonSchema?` | `any` |
| `inputSchema?` | `I` |
| `metadata?` | `M` |
| `name` | `string` |
| `outputJsonSchema?` | `any` |
| `outputSchema?` | `O` |
