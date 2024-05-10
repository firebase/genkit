# Function: run()

## run(name, func)

```ts
function run<T>(name: string, func: () => Promise<T>): Promise<T>
```

A flow steap that executes the provided function and memoizes the output.

### Type parameters

| Type parameter |
| :------ |
| `T` |

### Parameters

| Parameter | Type |
| :------ | :------ |
| `name` | `string` |
| `func` | () => `Promise`\<`T`\> |

### Returns

`Promise`\<`T`\>

### Source

[flow/src/steps.ts:31](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/flow/src/steps.ts#L31)

## run(name, input, func)

```ts
function run<T>(
   name: string, 
   input: any, 
func: () => Promise<T>): Promise<T>
```

A flow steap that executes the provided function and memoizes the output.

### Type parameters

| Type parameter |
| :------ |
| `T` |

### Parameters

| Parameter | Type |
| :------ | :------ |
| `name` | `string` |
| `input` | `any` |
| `func` | () => `Promise`\<`T`\> |

### Returns

`Promise`\<`T`\>

### Source

[flow/src/steps.ts:32](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/flow/src/steps.ts#L32)
