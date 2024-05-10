# Interface: GenerateStreamResponse\<O\>

## Type parameters

| Type parameter | Value |
| :------ | :------ |
| `O` *extends* `z.ZodTypeAny` | `z.ZodTypeAny` |

## Properties

| Property | Type |
| :------ | :------ |
| `response` | () => `Promise`\<[`GenerateResponse`](../classes/GenerateResponse.md)\<`O`\>\> |
| `stream` | () => `AsyncIterable`\<\{ `"content"`: ( \| \{ `"data"`: `unknown`; `"media"`: `undefined`; `"metadata"`: `Record`\<`string`, `unknown`\>; `"text"`: `string`; `"toolRequest"`: `undefined`; `"toolResponse"`: `undefined`; \} \| \{ `"data"`: `unknown`; `"media"`: \{ `"contentType"`: `string`; `"url"`: `string`; \}; `"metadata"`: `Record`\<`string`, `unknown`\>; `"text"`: `undefined`; `"toolRequest"`: `undefined`; `"toolResponse"`: `undefined`; \} \| \{ `"data"`: `unknown`; `"media"`: `undefined`; `"metadata"`: `Record`\<`string`, `unknown`\>; `"text"`: `undefined`; `"toolRequest"`: \{ `"input"`: `unknown`; `"name"`: `string`; `"ref"`: `string`; \}; `"toolResponse"`: `undefined`; \} \| \{ `"data"`: `unknown`; `"media"`: `undefined`; `"metadata"`: `Record`\<`string`, `unknown`\>; `"text"`: `undefined`; `"toolRequest"`: `undefined`; `"toolResponse"`: \{ `"name"`: `string`; `"output"`: `unknown`; `"ref"`: `string`; \}; \} \| \{ `"data"`: `unknown`; `"media"`: `undefined`; `"metadata"`: `Record`\<`string`, `unknown`\>; `"text"`: `undefined`; `"toolRequest"`: `undefined`; `"toolResponse"`: `undefined`; \})[]; `"custom"`: `unknown`; `"index"`: `number`; \}\> |
