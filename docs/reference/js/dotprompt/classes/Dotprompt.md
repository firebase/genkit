# Class: Dotprompt\<Variables\>

## Type parameters

| Type parameter | Value |
| :------ | :------ |
| `Variables` | `unknown` |

## Implements

- `PromptMetadata`

## Constructors

### new Dotprompt()

```ts
new Dotprompt<Variables>(options: PromptMetadata<ZodTypeAny, ZodTypeAny>, template: string): Dotprompt<Variables>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `options` | `PromptMetadata`\<`ZodTypeAny`, `ZodTypeAny`\> |
| `template` | `string` |

#### Returns

[`Dotprompt`](Dotprompt.md)\<`Variables`\>

#### Source

[plugins/dotprompt/src/prompt.ts:103](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/dotprompt/src/prompt.ts#L103)

## Properties

| Property | Modifier | Type |
| :------ | :------ | :------ |
| `_render` | `private` | (`input`: `Variables`) => \{ `"content"`: ( \| \{ `"data"`: `unknown`; `"media"`: `undefined`; `"metadata"`: `Record`\<`string`, `unknown`\>; `"text"`: `string`; `"toolRequest"`: `undefined`; `"toolResponse"`: `undefined`; \} \| \{ `"data"`: `unknown`; `"media"`: \{ `"contentType"`: `string`; `"url"`: `string`; \}; `"metadata"`: `Record`\<`string`, `unknown`\>; `"text"`: `undefined`; `"toolRequest"`: `undefined`; `"toolResponse"`: `undefined`; \} \| \{ `"data"`: `unknown`; `"media"`: `undefined`; `"metadata"`: `Record`\<`string`, `unknown`\>; `"text"`: `undefined`; `"toolRequest"`: \{ `"input"`: `unknown`; `"name"`: `string`; `"ref"`: `string`; \}; `"toolResponse"`: `undefined`; \} \| \{ `"data"`: `unknown`; `"media"`: `undefined`; `"metadata"`: `Record`\<`string`, `unknown`\>; `"text"`: `undefined`; `"toolRequest"`: `undefined`; `"toolResponse"`: \{ `"name"`: `string`; `"output"`: `unknown`; `"ref"`: `string`; \}; \} \| \{ `"data"`: `unknown`; `"media"`: `undefined`; `"metadata"`: `Record`\<`string`, `unknown`\>; `"text"`: `undefined`; `"toolRequest"`: `undefined`; `"toolResponse"`: `undefined`; \})[]; `"role"`: `"model"` \| `"tool"` \| `"user"` \| `"system"`; \}[] |
| `candidates?` | `public` | `number` |
| `config?` | `public` | `any` |
| `hash` | `public` | `string` |
| `input?` | `public` | \{ `"default"`: `any`; `"jsonSchema"`: `any`; `"schema"`: `ZodTypeAny`; \} |
| `input.default?` | `public` | `any` |
| `input.jsonSchema?` | `public` | `any` |
| `input.schema?` | `public` | `ZodTypeAny` |
| `metadata` | `public` | `undefined` \| `Record`\<`string`, `any`\> |
| `model?` | `public` | `ModelArgument`\<`ZodTypeAny`\> |
| `name` | `public` | `string` |
| `output?` | `public` | \{ `"format"`: `"json"` \| `"text"` \| `"media"`; `"jsonSchema"`: `any`; `"schema"`: `ZodTypeAny`; \} |
| `output.format?` | `public` | `"json"` \| `"text"` \| `"media"` |
| `output.jsonSchema?` | `public` | `any` |
| `output.schema?` | `public` | `ZodTypeAny` |
| `template` | `public` | `string` |
| `tools?` | `public` | `ToolArgument`\<`ZodTypeAny`, `ZodTypeAny`\>[] |
| `variant?` | `public` | `string` |

## Methods

### \_generateOptions()

```ts
private _generateOptions(options: PromptGenerateOptions<Variables>): GenerateOptions<ZodTypeAny, ZodTypeAny>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `options` | `PromptGenerateOptions`\<`Variables`\> |

#### Returns

`GenerateOptions`\<`ZodTypeAny`, `ZodTypeAny`\>

#### Source

[plugins/dotprompt/src/prompt.ts:161](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/dotprompt/src/prompt.ts#L161)

***

### define()

```ts
define(): void
```

#### Returns

`void`

#### Source

[plugins/dotprompt/src/prompt.ts:145](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/dotprompt/src/prompt.ts#L145)

***

### generate()

```ts
generate(opt: PromptGenerateOptions<Variables>): Promise<GenerateResponse<unknown>>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `opt` | `PromptGenerateOptions`\<`Variables`\> |

#### Returns

`Promise`\<`GenerateResponse`\<`unknown`\>\>

#### Source

[plugins/dotprompt/src/prompt.ts:185](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/dotprompt/src/prompt.ts#L185)

***

### generateStream()

```ts
generateStream(opt: PromptGenerateOptions<Variables>): Promise<GenerateStreamResponse<ZodTypeAny>>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `opt` | `PromptGenerateOptions`\<`Variables`\> |

#### Returns

`Promise`\<`GenerateStreamResponse`\<`ZodTypeAny`\>\>

#### Source

[plugins/dotprompt/src/prompt.ts:191](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/dotprompt/src/prompt.ts#L191)

***

### render()

```ts
render(opt: PromptGenerateOptions<Variables>): GenerateOptions<ZodTypeAny, ZodTypeAny>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `opt` | `PromptGenerateOptions`\<`Variables`\> |

#### Returns

`GenerateOptions`\<`ZodTypeAny`, `ZodTypeAny`\>

#### Source

[plugins/dotprompt/src/prompt.ts:181](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/dotprompt/src/prompt.ts#L181)

***

### renderMessages()

```ts
renderMessages(input?: Variables, context?: {
  "content": ({
     "media": undefined;
     "text": string;
    } | {
     "media": {
        "contentType": string;
        "url": string;
       };
     "text": undefined;
    })[];
  "metadata": Record<string, any>;
 }[]): {
  "content": (
     | {
     "data": unknown;
     "media": undefined;
     "metadata": Record<string, unknown>;
     "text": string;
     "toolRequest": undefined;
     "toolResponse": undefined;
    }
     | {
     "data": unknown;
     "media": {
        "contentType": string;
        "url": string;
       };
     "metadata": Record<string, unknown>;
     "text": undefined;
     "toolRequest": undefined;
     "toolResponse": undefined;
    }
     | {
     "data": unknown;
     "media": undefined;
     "metadata": Record<string, unknown>;
     "text": undefined;
     "toolRequest": {
        "input": unknown;
        "name": string;
        "ref": string;
       };
     "toolResponse": undefined;
    }
     | {
     "data": unknown;
     "media": undefined;
     "metadata": Record<string, unknown>;
     "text": undefined;
     "toolRequest": undefined;
     "toolResponse": {
        "name": string;
        "output": unknown;
        "ref": string;
       };
    }
     | {
     "data": unknown;
     "media": undefined;
     "metadata": Record<string, unknown>;
     "text": undefined;
     "toolRequest": undefined;
     "toolResponse": undefined;
    })[];
  "role": "model" | "tool" | "user" | "system";
 }[]
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `input`? | `Variables` |
| `context`? | \{ `"content"`: (\{ `"media"`: `undefined`; `"text"`: `string`; \} \| \{ `"media"`: \{ `"contentType"`: `string`; `"url"`: `string`; \}; `"text"`: `undefined`; \})[]; `"metadata"`: `Record`\<`string`, `any`\>; \}[] |

#### Returns

\{
  `"content"`: (
     \| \{
     `"data"`: `unknown`;
     `"media"`: `undefined`;
     `"metadata"`: `Record`\<`string`, `unknown`\>;
     `"text"`: `string`;
     `"toolRequest"`: `undefined`;
     `"toolResponse"`: `undefined`;
    \}
     \| \{
     `"data"`: `unknown`;
     `"media"`: \{
        `"contentType"`: `string`;
        `"url"`: `string`;
       \};
     `"metadata"`: `Record`\<`string`, `unknown`\>;
     `"text"`: `undefined`;
     `"toolRequest"`: `undefined`;
     `"toolResponse"`: `undefined`;
    \}
     \| \{
     `"data"`: `unknown`;
     `"media"`: `undefined`;
     `"metadata"`: `Record`\<`string`, `unknown`\>;
     `"text"`: `undefined`;
     `"toolRequest"`: \{
        `"input"`: `unknown`;
        `"name"`: `string`;
        `"ref"`: `string`;
       \};
     `"toolResponse"`: `undefined`;
    \}
     \| \{
     `"data"`: `unknown`;
     `"media"`: `undefined`;
     `"metadata"`: `Record`\<`string`, `unknown`\>;
     `"text"`: `undefined`;
     `"toolRequest"`: `undefined`;
     `"toolResponse"`: \{
        `"name"`: `string`;
        `"output"`: `unknown`;
        `"ref"`: `string`;
       \};
    \}
     \| \{
     `"data"`: `unknown`;
     `"media"`: `undefined`;
     `"metadata"`: `Record`\<`string`, `unknown`\>;
     `"text"`: `undefined`;
     `"toolRequest"`: `undefined`;
     `"toolResponse"`: `undefined`;
    \})[];
  `"role"`: `"model"` \| `"tool"` \| `"user"` \| `"system"`;
 \}[]

#### Source

[plugins/dotprompt/src/prompt.ts:133](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/dotprompt/src/prompt.ts#L133)

***

### renderText()

```ts
renderText(input: Variables, context?: {
  "content": ({
     "media": undefined;
     "text": string;
    } | {
     "media": {
        "contentType": string;
        "url": string;
       };
     "text": undefined;
    })[];
  "metadata": Record<string, any>;
 }[]): string
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `input` | `Variables` |
| `context`? | \{ `"content"`: (\{ `"media"`: `undefined`; `"text"`: `string`; \} \| \{ `"media"`: \{ `"contentType"`: `string`; `"url"`: `string`; \}; `"text"`: `undefined`; \})[]; `"metadata"`: `Record`\<`string`, `any`\>; \}[] |

#### Returns

`string`

#### Source

[plugins/dotprompt/src/prompt.ts:118](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/dotprompt/src/prompt.ts#L118)

***

### toJSON()

```ts
toJSON(): PromptData
```

#### Returns

`PromptData`

#### Source

[plugins/dotprompt/src/prompt.ts:141](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/dotprompt/src/prompt.ts#L141)

***

### fromAction()

```ts
static fromAction(action: PromptAction<ZodTypeAny>): Dotprompt<unknown>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `action` | `PromptAction`\<`ZodTypeAny`\> |

#### Returns

[`Dotprompt`](Dotprompt.md)\<`unknown`\>

#### Source

[plugins/dotprompt/src/prompt.ts:89](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/dotprompt/src/prompt.ts#L89)

***

### parse()

```ts
static parse(name: string, source: string): Dotprompt<unknown>
```

#### Parameters

| Parameter | Type |
| :------ | :------ |
| `name` | `string` |
| `source` | `string` |

#### Returns

[`Dotprompt`](Dotprompt.md)\<`unknown`\>

#### Source

[plugins/dotprompt/src/prompt.ts:70](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/plugins/dotprompt/src/prompt.ts#L70)
