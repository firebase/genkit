# Dotprompt

Dotprompt is a text format for GenAI prompts that helps you write and organize your prompts. To use
Dotprompt, first create a `prompts` directory in your project root and then create a `.prompt` file
in that directory. Here's a simple example we might call `greeting.prompt`:

```hbs
---
model: vertex-ai/gemini-1.0-pro
config:
  temperature: 0.9
variables:
  type: object
  properties:
    location: {type: string}
    style: {type: string}
    name: {type: string}
  required: [location]
---

You are the world's most welcoming AI assistant and are currently working at {{location}}.

Greet a guest{{#if name}} named {{name}}{{/if}}{{#if style}} in the style of {{style}}.
```

To use this prompt, import the `@genkit-ai/dotprompt` library and load the prompt using
`prompt('file_name')`:

```ts
import { prompt } from '@genkit-ai/dotprompt';

const greetingPrompt = prompt('greeting');

const result = await recipePrompt.generate({
  variables: {
    location: "the beach",
    style: "a fancy pirate",
  },
});

console.log(result.text());
```

Dotprompt's syntax is based on the [Handlebars](https://handlebarsjs.com/guide/) templating
language. You can use the `if`, `unless`, and `each` helpers to add conditional portions of
your prompt or iterate through structured content.

## Multi-message prompts with `{{role "<role_name>"}}`

By default Dotprompt constructs a single message with a `"user"` role. Some prompts are
best expressed as a combination of multiple messages, such as a system prompt.

The `{{role}}` helper provides a simple way to construct multi-message prompts:

```hbs
---
model: vertex-ai/gemini-1.0-pro
variables:
  type: object
  properties:
    userQuestion: {type: string}
  required: [userQuestion]
---

{{role "system"}}
You are a helpful AI assistant that really loves to talk about puppies. Try to work puppies
into all of your conversations.
{{role "user"}}
{{userQuestion}}
```

## Multi-modal prompts with `{{media url=<variable>}}`

For models that support multimodal input such as images, you can use the `{{media}}` helper:

```hbs
---
model: vertex-ai/gemini-1.0-pro-vision
variables:
  type: object
  properties:
    photoUrl: {type: string}
  required: [userQuestion]
---

Describe this image in a detailed paragraph:

{{image url=photoUrl}}
```

The URL can be `https://` or base64-encoded `data:` URIs for "inline" image usage. In code
this would be:

```ts
const describeImagePrompt = await prompt('describe_image');

const result = await describeImagePrompt.generate({
  variables: {
    photoUrl: 'https://example.com/image.png',
  },
});

console.log(result.text());
```

## Prompt Variants

Because prompt files are just text, you can (and should!) commit them to your version control
system, giving you an easy ability to compare changes over time. However, oftentimes tweaked
versions of prompts can only be fully tested in a production environment side-by-side with
existing versions. Dotprompt supports this through its **variants** feature.

To create a variant, simply create a `[name].[variant].prompt` file. For instance, if I was
using GPT-3.5 Turbo in my prompt but wanted to see if Gemini 1.0 Pro would perform better,
I might create two files:

* `my_prompt.prompt`: the "baseline" prompt
* `my_prompt.gemini.prompt`: a variant named "gemini"

To use a prompt variant, specify the `variant` option when loading:

```ts
const myPrompt = await prompt('my_prompt', {variant: 'gemini'});
```

The prompt loader will look for a recognized variant of that name, or fall back to the
baseline if none exists. This means you can use conditional loading based on whatever
criteria makes sense for your application:

```ts
const myPrompt = await prompt('my_prompt', {
  variant: isBetaTester(user) ? 'gemini' : null
});
```

The name of the variant is included in the metadata in generation traces, so you can
compare and contrast actual performance between variants in the Genkit trace inspector.