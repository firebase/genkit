# Function: defineTool()

```ts
function defineTool<I, O>(__namedParameters: {
  "description": string;
  "inputJsonSchema": any;
  "inputSchema": I;
  "metadata": Record<string, any>;
  "name": string;
  "outputJsonSchema": any;
  "outputSchema": O;
}, fn: (input: TypeOf<I>) => Promise<TypeOf<O>>): ToolAction<I, O>
```

## Type parameters

| Type parameter |
| :------ |
| `I` *extends* `ZodType`\<`any`, `any`, `any`, `I`\> |
| `O` *extends* `ZodType`\<`any`, `any`, `any`, `O`\> |

## Parameters

| Parameter | Type |
| :------ | :------ |
| `__namedParameters` | `object` |
| `__namedParameters.description` | `string` |
| `__namedParameters.inputJsonSchema`? | `any` |
| `__namedParameters.inputSchema`? | `I` |
| `__namedParameters.metadata`? | `Record`\<`string`, `any`\> |
| `__namedParameters.name` | `string` |
| `__namedParameters.outputJsonSchema`? | `any` |
| `__namedParameters.outputSchema`? | `O` |
| `fn` | (`input`: `TypeOf`\<`I`\>) => `Promise`\<`TypeOf`\<`O`\>\> |

## Returns

[`ToolAction`](../type-aliases/ToolAction.md)\<`I`, `O`\>

## Source

[ai/src/tool.ts:100](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/ai/src/tool.ts#L100)
