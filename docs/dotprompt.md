# Managing prompts with Dotprompt

Firebase Genkit provides the Dotprompt plugin and text format to help you write
and organize your generative AI prompts.

Dotprompt is designed around the premise that _prompts are code_. You write and
maintain your prompts in specially-formatted files called dotprompt files, track
changes to them using the same version control system that you use for your
code, and you deploy them along with the code that calls your generative AI
models.

To use Dotprompt, first create a `prompts` directory in your project root and
then create a `.prompt` file in that directory. Here's a simple example you
might call `greeting.prompt`:

```none
---
model: vertexai/gemini-1.5-flash
config:
  temperature: 0.9
input:
  schema:
    location: string
    style?: string
    name?: string
  default:
    location: a restaurant
---

You are the world's most welcoming AI assistant and are currently working at {{location}}.

Greet a guest{{#if name}} named {{name}}{{/if}}{{#if style}} in the style of {{style}}{{/if}}.
```

To use this prompt, install the `dotprompt` plugin, and import the `promptRef` function from
the `@genkit/dotprompt` library:

```ts
import { dotprompt, promptRef } from '@genkit/dotprompt';

configureGenkit({ plugins: [dotprompt()] });
```

Then, load the prompt using `promptRef('file_name')`:

```ts
const greetingPrompt = promptRef('greeting');

const result = await greetingPrompt.generate({
  input: {
    location: 'the beach',
    style: 'a fancy pirate',
  },
});

console.log(result.text());
```

Dotprompt's syntax is based on the [Handlebars](https://handlebarsjs.com/guide/)
templating language. You can use the `if`, `unless`, and `each` helpers to add
conditional portions to your prompt or iterate through structured content. The
file format utilizes YAML frontmatter to provide metadata for a prompt inline
with the template.

## Defining Input/Output Schemas

Dotprompt includes a compact, YAML-optimized schema definition format called
Picoschema to make it easy to define the most important attributes of a schema
for LLM usage. Here's an example of a schema for an article:

```yaml
schema:
  title: string # string, number, and boolean types are defined like this
  subtitle?: string # optional fields are marked with a `?`
  draft?: boolean, true when in draft state
  status?(enum, approval status): [PENDING, APPROVED]
  date: string, the date of publication e.g. '2024-04-09' # descriptions follow a comma
  tags(array, relevant tags for article): string # arrays are denoted via parentheses
  authors(array):
    name: string
    email?: string
  metadata?(object): # objects are also denoted via parentheses
    updatedAt?: string, ISO timestamp of last update
    approvedBy?: integer, id of approver
  extra?: any, arbitrary extra data
  (*): string, wildcard field
```

The above schema is equivalent to the following TypeScript interface:

```ts
interface Article {
  title: string;
  subtitle?: string | null;
  /** true when in draft state */
  draft?: boolean | null;
  /** approval status */
  status?: 'PENDING' | 'APPROVED' | null;
  /** the date of publication e.g. '2024-04-09' */
  date: string;
  /** relevant tags for article */
  tags: string[];
  authors: {
    name: string;
    email?: string | null;
  }[];
  metadata?: {
    /** ISO timestamp of last update */
    updatedAt?: string | null;
    /** id of approver */
    approvedBy?: number | null;
  } | null;
  /** arbitrary extra data */
  extra?: any;
  /** wildcard field */
  [additionalField: string]: string;
}
```

Picoschema supports scalar types `string`, `integer`, `number`, `boolean`, and `any`.
For objects, arrays, and enums they are denoted by a parenthetical after the field name.

Objects defined by Picoschema have all properties as required unless denoted optional
by `?`, and do not allow additional properties. When a property is marked as optional,
it is also made nullable to provide more leniency for LLMs to return null instead of
omitting a field.

In an object definition, the special key `(*)` can be used to declare a "wildcard"
field definition. This will match any additional properties not supplied by an
explicit key.

Picoschema does not support many of the capabilities of full JSON schema. If you
require more robust schemas, you may supply a JSON Schema instead:

```yaml
output:
  schema:
    type: object
    properties:
      field1:
        type: number
        minimum: 20
```

### Leveraging Reusable Schemas

In addition to directly defining schemas in the `.prompt` file, you can reference
a schema registered with `defineSchema` by name. To register a schema:

```ts
import { defineSchema } from '@genkit/core';
import { z } from 'zod';

const MySchema = defineSchema(
  'MySchema',
  z.object({
    field1: z.string(),
    field2: z.number(),
  })
);
```

Within your prompt, you can provide the name of the registered schema:

```yaml
# myPrompt.prompt
---
model: vertexai/gemini-1.5-flash
output:
  schema: MySchema
---
```

The Dotprompt library will automatically resolve the name to the underlying
registered Zod schema. You can then utilize the schema to strongly type the
output of a Dotprompt:

```ts
import { promptRef } from "@genkit/dotprompt";

const myPrompt = promptRef("myPrompt");

const result = await myPrompt.generate<typeof MySchema>({...});

// now strongly typed as MySchema
result.output();
```

## Overriding Prompt Metadata

While `.prompt` files allow you to embed metadata such as model configuration in
the file itself, you can also override these values on a per-call basis:

```ts
const result = await greetingPrompt.generate({
  model: 'vertexai/gemini-1.5-pro',
  config: {
    temperature: 1.0,
  },
  input: {
    location: 'the beach',
    style: 'a fancy pirate',
  },
});
```

## Structured output

You can set the format and output schema of a prompt to coerce into JSON:

```none
---
model: vertexai/gemini-1.5-flash
input:
  schema:
    theme: string
output:
  format: json
  schema:
    name: string
    price: integer
    ingredients(array): string
---

Generate a menu item that could be found at a {{theme}} themed restaurant.
```

When generating a prompt with structured output, use the `output()` helper to
retrieve and validate it:

```ts
const createMenuPrompt = promptRef('create_menu');

const menu = await createMenuPrompt.generate({
  input: {
    theme: 'banana',
  },
});

console.log(menu.output());
```

Output conformance is achieved by inserting additional instructions into the
prompt. By default, it is appended to the end of the last message generated
by the prompt. You can manually reposition it using the `{{section "output"}}`
helper.

```none
This is a prompt that manually positions output instructions.

== Output Instructions

{{section "output"}}

== Other Instructions

This will come after the output instructions.
```

## Multi-message prompts

By default, Dotprompt constructs a single message with a `"user"` role. Some
prompts are best expressed as a combination of multiple messages, such as a
system prompt.

The `{{role}}` helper provides a simple way to construct multi-message prompts:

```none
---
model: vertexai/gemini-1.5-flash
input:
  schema:
    userQuestion: string
---

{{role "system"}}
You are a helpful AI assistant that really loves to talk about food. Try to work
food items into all of your conversations.
{{role "user"}}
{{userQuestion}}
```

## Multi-Turn Prompts and History

Dotprompt supports multi-turn prompts by passing the `history` option into the
`generate` method:

```ts
const result = await multiTurnPrompt.generate({
  history: [
    { role: 'user', content: [{ text: 'Hello.' }] },
    { role: 'model', content: [{ text: 'Hi there!' }] },
  ],
});
```

By default, history will be inserted before the final message generated by
the prompt. However, you can manually position history using the `{{history}}`
helper:

```none
{{role "system"}}
This is the system prompt.
{{history}}
{{role "user"}}
This is a user message.
{{role "model"}}
This is a model message.
{{role "user"}}
This is the final user message.
```

## Multi-modal prompts

For models that support multimodal input such as images alongside text, you can
use the `{{media}}` helper:

```none
---
model: vertexai/gemini-1.5-flash
input:
  schema:
    photoUrl: string
---

Describe this image in a detailed paragraph:

{{media url=photoUrl}}
```

The URL can be `https://` or base64-encoded `data:` URIs for "inline" image
usage. In code, this would be:

```ts
const describeImagePrompt = promptRef('describe_image');

const result = await describeImagePrompt.generate({
  input: {
    photoUrl: 'https://example.com/image.png',
  },
});

console.log(result.text());
```

## Partials

Partials are reusable templates that can be included inside any prompt. Partials
can be especially helpful for related prompts that share common behavior.

When loading a prompt directory, any file prefixed with `_` is considered a
partial. So a file `_personality.prompt` might contain:

```none
You should speak like a {{#if style}}{{style}}{{else}}helpful assistant.{{/else}}.
```

This can then be included in other prompts:

```none
---
model: vertexai/gemini-1.5-flash
input:
  schema:
    name: string
    style?: string
---

{{ role "system" }}
{{>personality style=style}}

{{ role "user" }}
Give the user a friendly greeting.

User's Name: {{name}}
```

Partials are inserted using the `{{>NAME_OF_PARTIAL args...}}` syntax. If no
arguments are provided to the partial, it executes with the same context as the
parent prompt.

Partials accept both named arguments as above or a single positional argument
representing the context. This can be helpful for e.g. rendering members of a list.

```
# _destination.prompt
- {{name}} ({{country}})

# chooseDestination.prompt
Help the user decide between these vacation destinations:
{{#each destinations}}
{{>destination this}}{{/each}}
```

### Defining Partials in Code

You may also define partials in code using `definePartial`:

```ts
import { definePartial } from '@genkit/dotprompt';

definePartial(
  'personality',
  'Talk like a {{#if style}}{{style}}{{else}}helpful assistant{{/if}}.'
);
```

Code-defined partials are available in all prompts.

## Prompt Variants

Because prompt files are just text, you can (and should!) commit them to your
version control system, allowing you to compare changes over time easily.
Often times, tweaked versions of prompts can only be fully tested in a
production environment side-by-side with existing versions. Dotprompt supports
this through its **variants** feature.

To create a variant, create a `[name].[variant].prompt` file. For instance, if
you were using Gemini 1.5 Flash in your prompt but wanted to see if Gemini 1.5
Pro would perform better, you might create two files:

- `my_prompt.prompt`: the "baseline" prompt
- `my_prompt.gemini15pro.prompt`: a variant named "gemini15pro"

To use a prompt variant, specify the `variant` option when loading:

```ts
const myPrompt = promptRef('my_prompt', { variant: 'gemini15pro' });
```

The name of the variant is included in the metadata of generation traces, so you
can compare and contrast actual performance between variants in the Genkit trace
inspector.

## Defining Custom Helpers

You can define custom helpers to process and manage data inside of a prompt. Helpers
are registered globally using `defineHelper`:

```ts
import { defineHelper } from '@genkit/dotprompt';

defineHelper('shout', (text: string) => text.toUpperCase());
```

Once a helper is defined you can use it in any prompt:

```none
---
model: vertexai/gemini-1.5-flash
input:
  schema:
    name: string
---

HELLO, {{shout name}}!!!
```

For more information about the arguments passed into helpers, see the
[Handlebars documentation](https://handlebarsjs.com/guide/#custom-helpers) on creating
custom helpers.

## Alternate ways to load and define prompts

Dotprompt is optimized for organization in the prompt directory. However, there
are a few other ways to load and define prompts:

- `loadPromptFile`: Load a prompt from a file in the prompt directory.
- `loadPromptUrl`: Load a prompt from a URL.
- `defineDotprompt`: Define a prompt in code.

Examples:

```ts
import {
  loadPromptFile,
  loadPromptUrl,
  defineDotprompt,
} from '@genkit/dotprompt';
import path from 'path';
import { z } from 'zod';

// Load a prompt from a file
const myPrompt = await loadPromptFile(
  path.resolve(__dirname, './path/to/my_prompt.prompt')
);

// Load a prompt from a URL
const myPrompt = await loadPromptUrl('https://example.com/my_prompt.prompt');

// Define a prompt in code
const myPrompt = defineDotprompt(
  {
    model: 'vertexai/gemini-1.5-flash',
    input: {
      schema: z.object({
        name: z.string(),
      }),
    },
  },
  `Hello {{name}}, how are you today?`
);
```
