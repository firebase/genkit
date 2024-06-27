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
model: vertexai/gemini-1.0-pro
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

To use this prompt, install the `dotprompt` plugin, and import the `prompt` function from
the `@genkit-ai/dotprompt` library:

```ts
import { dotprompt, prompt } from '@genkit-ai/dotprompt';

configureGenkit({ plugins: [dotprompt()] });
```

Then, load the prompt using `prompt('file_name')`:

```ts
const greetingPrompt = await prompt('greeting');

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

## Defining Input/Output Schemas with Picoschema

Dotprompt includes a compact, YAML-optimized schema definition format called
Picoschema to make it easy to define the most important attributs of a schema
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

## Overriding Prompt Metadata

While `.prompt` files allow you to embed metadata such as model configuration in
the file itself, you can also override these values on a per-call basis:

```ts
const result = await greetingPrompt.generate({
  model: 'google-genai/gemini-pro',
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
model: vertexai/gemini-1.0-pro
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
const createMenuPrompt = await prompt('create_menu');

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
model: vertexai/gemini-1.0-pro
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
model: vertexai/gemini-1.0-pro-vision
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
const describeImagePrompt = await prompt('describe_image');

const result = await describeImagePrompt.generate({
  input: {
    photoUrl: 'https://example.com/image.png',
  },
});

console.log(result.text());
```

## Prompt Variants

Because prompt files are just text, you can (and should!) commit them to your
version control system, allowing you to compare changes over time easily.
Often times, tweaked versions of prompts can only be fully tested in a
production environment side-by-side with existing versions. Dotprompt supports
this through its **variants** feature.

To create a variant, create a `[name].[variant].prompt` file. For instance, if
you were using Gemini 1.0 Pro in your prompt but wanted to see if Gemini 1.5 Pro
would perform better, you might create two files:

- `my_prompt.prompt`: the "baseline" prompt
- `my_prompt.gemini15.prompt`: a variant named "gemini"

To use a prompt variant, specify the `variant` option when loading:

```ts
const myPrompt = await prompt('my_prompt', { variant: 'gemini15' });
```

The prompt loader will attempt to load the variant of that name, and fall back
to the baseline if none exists. This means you can use conditional loading based
on whatever criteria makes sense for your application:

```ts
const myPrompt = await prompt('my_prompt', {
  variant: isBetaTester(user) ? 'gemini15' : null,
});
```

The name of the variant is included in the metadata of generation traces, so you
can compare and contrast actual performance between variants in the Genkit trace
inspector.

## Defining Custom Helpers

You can define custom helpers to process and manage data inside of a prompt. Helpers
are registered globally using `defineHelper`:

```ts
import { defineHelper } from '@genkit-ai/dotprompt';

defineHelper('shout', (text: string) => text.toUpperCase());
```

Once a helper is defined you can use it in any prompt:

```none
---
model: vertexai/gemini-1.5-pro
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
} from '@genkit-ai/dotprompt';
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
    model: 'vertexai/gemini-1.0-pro',
    input: {
      schema: z.object({
        name: z.string(),
      }),
    },
  },
  `Hello {{name}}, how are you today?`
);
```
