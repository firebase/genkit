# Managing prompts with Dotprompt

Genkit provides the Dotprompt library and text format to help you write and
organize your generative AI prompts.

Prompt manipulation is the primary way that you, as an app developer, influence
the output of generative AI models. For example, when using LLMs, you can craft
prompts that influence the tone, format, length, and other characteristics of
the models’ responses.

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

To use this prompt, import the `@genkit-ai/dotprompt` library and load the prompt using
`prompt('file_name')`:

```ts
import { prompt } from '@genkit-ai/dotprompt';

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
  date: string, the date of publication e.g. '2024-04-09' # descriptions follow a comma
  tags(array, relevant tags for article): string # arrays are denoted via parentheses
  authors(array):
    name: string
    email?: string
  metadata?(object): # objects are also denoted via parentheses
    updatedAt?: string, ISO timestamp of last update
    approvedBy?: integer, id of approver
```

The above schema is equivalent to the following TypeScript interface:

```ts
interface Article {
  title: string;
  subtitle?: string;
  /** true when in draft state */
  draft?: boolean;
  /** the date of publication e.g. '2024-04-09' */
  date: string;
  /** relevant tags for article */
  tags: string[];
  authors: {
    name: string;
    email?: string;
  }[];
  metadata?: {
    /** ISO timestamp of last update */
    updatedAt?: string;
    /** id of approver */
    approvedBy?: number;
  };
}
```

Picoschema supports scalar types `string`, `integer`, `number`, and `boolean`. For
objects and arrays, they are denoted by a parenthetical after the field name.

Objects defined by Picoschema have all properties as required unless denoted optional
by `?`, and do not allow additional properties.

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
    location: string
output:
  format: json
  schema:
    name: string
    hitPoints: integer
    description: string
---

Generate a tabletop RPG character that would be found in {{location}}.
```

When generating a prompt with structured output, use the `output()` helper to
retrieve and validate it:

```ts
const characterPrompt = await prompt('create_character');

const character = await characterPrompt.generate({
  input: {
    location: 'the beach',
  },
});

console.log(character.output());
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
You are a helpful AI assistant that really loves to talk about puppies. Try to work puppies
into all of your conversations.
{{role "user"}}
{{userQuestion}}
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

## Alternate ways to load and define prompts

Dotprompt is optimized for organization in the prompt directory. However, there
are a few other ways to load and define prompts:

- `loadPromptFile`: Load a prompt from a file in the prompt directory.
- `loadPromptUrl`: Load a prompt from a URL.
- `definePrompt`: Define a prompt in code.

Examples:

```ts
import {
  loadPromptFile,
  loadPromptUrl,
  definePrompt,
} from '@genkit-ai/dotprompt';
import { z } from 'zod';

// Load a prompt from a file
const myPrompt = await loadPromptFile('./path/to/my_prompt.prompt');

// Load a prompt from a URL
const myPrompt = await loadPromptUrl('https://example.com/my_prompt.prompt');

// Define a prompt in code
const myPrompt = definePrompt(
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
