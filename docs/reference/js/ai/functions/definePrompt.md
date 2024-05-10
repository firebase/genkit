# Function: definePrompt()

```ts
function definePrompt<I>(__namedParameters: {
  "description": string;
  "inputJsonSchema": any;
  "inputSchema": I;
  "metadata": Record<string, any>;
  "name": string;
}, fn: PromptFn<I>): PromptAction<I>
```

## Type parameters

| Type parameter |
| :------ |
| `I` *extends* `ZodType`\<`any`, `any`, `any`, `I`\> |

## Parameters

| Parameter | Type |
| :------ | :------ |
| `__namedParameters` | `object` |
| `__namedParameters.description`? | `string` |
| `__namedParameters.inputJsonSchema`? | `any` |
| `__namedParameters.inputSchema`? | `I` |
| `__namedParameters.metadata`? | `Record`\<`string`, `any`\> |
| `__namedParameters.name` | `string` |
| `fn` | `PromptFn`\<`I`\> |

## Returns

[`PromptAction`](../type-aliases/PromptAction.md)\<`I`\>

## Source

[ai/src/prompt.ts:50](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/ai/src/prompt.ts#L50)
