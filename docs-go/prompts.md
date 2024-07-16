# Prompts

Prompt manipulation is the primary way that you, as an app developer, influence
the output of generative AI models. For example, when using LLMs, you can craft
prompts that influence the tone, format, length, and other characteristics of
the models’ responses.

Genkit is designed around the premise that _prompts are code_. You write and
maintain your prompts in source files, track changes to them using the same version
control system that you use for your code, and you deploy them along with the code
that calls your generative AI models.

Most developers will find that the included [Dotprompt](./dotprompt.md) library
meets their needs for working with prompts in Genkit. However, alternative
approaches are also supported by working with prompts directly.

## Defining prompts

Genkit's generation helper functions accept string prompts, and you can
call models this way for straight-forward use cases.

- {Go}

  ```golang
  {% includecode github_path="firebase/genkit/go/internal/doc-snippets/prompts.go" region_tag="pr01" %}
  ```

In most cases, you'll need to include some user-provided inputs in your prompt.
You could define a function to render them like this:

- {Go}

  ```golang
  {% includecode github_path="firebase/genkit/go/internal/doc-snippets/prompts.go" region_tag="hello" %}
  ```

  ```golang
  {% includecode github_path="firebase/genkit/go/internal/doc-snippets/prompts.go" region_tag="pr02" %}
  ```

However, one shortcoming of defining prompts in your code is that testing requires executing
them as part of a flow. To facilitate more rapid iteration, Genkit provides a facility
to define your prompts and run them in the Developer UI.

- {Go}

  Use the `DefinePrompt` function to register your prompts with Genkit.

  ```golang
  {% includecode github_path="firebase/genkit/go/internal/doc-snippets/prompts.go" region_tag="pr03.1" %}
  ```

A prompt action defines a function that returns a `GenerateRequest`,
which can be used with any model. Optionally, you can also define an input schema
for the prompt, which is analagous to the input schema for a flow.
Prompts can also define any of the common model configuration options, such as
temperature or number of output tokens.

You can render this prompt to a model request with the provided helper function.
Provide the input variables expected by the prompt, and the model to call.

- {Go}

  ```golang
  {% includecode github_path="firebase/genkit/go/internal/doc-snippets/prompts.go" region_tag="pr03.2" %}
  ```

In the Genkit Developer UI, you can run any prompt you have defined in this way.
This allows you to experiment with individual prompts outside of the scope of
the flows in which they might be used.

## Dotprompt

Genkit includes the [Dotprompt](./dotprompt.md) library which adds additional
functionality to prompts.

- Loading prompts from `.prompt` source files
- Handlebars-based templates
- Support for multi-turn prompt templates and multimedia content
- Concise input and output schema definitions
- Fluent usage with `generate()`
