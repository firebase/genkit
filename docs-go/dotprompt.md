# Managing prompts with Dotprompt

Genkit provides the Dotprompt plugin and text format to help you write
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
{% verbatim %}---
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

Greet a guest{{#if name}} named {{name}}{{/if}}{{#if style}} in the style of {{style}}{{/if}}.{% endverbatim %}
```

To use this prompt, install the `dotprompt` plugin:

```posix-terminal
go get github.com/firebase/genkit/go/plugins/dotprompt
```

Then, load the prompt using `Open`:

```go
import "github.com/firebase/genkit/go/plugins/dotprompt"
```

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/dotprompt.go" region_tag="dot01_1" adjust_indentation="auto" %}
```

You can call the prompt's `Generate` method to render the template and pass it
to the model API in one step:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/dotprompt.go" region_tag="dot01_2" adjust_indentation="auto" %}
```

Or just render the template to a string:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/dotprompt.go" region_tag="dot01_3" adjust_indentation="auto" %}
```

Dotprompt's syntax is based on the [Handlebars](https://handlebarsjs.com/guide/)
templating language. You can use the `if`, `unless`, and `each` helpers to add
conditional portions to your prompt or iterate through structured content. The
file format utilizes YAML frontmatter to provide metadata for a prompt inline
with the template.

## Defining Input/Output Schemas with Picoschema

Dotprompt includes a compact, YAML-based schema definition format called
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

The above schema is equivalent to the following JSON schema:

```json
{
  "properties": {
    "metadata": {
      "properties": {
        "updatedAt": {
          "type": "string",
          "description": "ISO timestamp of last update"
        },
        "approvedBy": {
          "type": "integer",
          "description": "id of approver"
        }
      },
      "type": "object"
    },
    "title": {
      "type": "string"
    },
    "subtitle": {
      "type": "string"
    },
    "draft": {
      "type": "boolean",
      "description": "true when in draft state"
    },
    "date": {
      "type": "string",
      "description": "the date of publication e.g. '2024-04-09'"
    },
    "tags": {
      "items": {
        "type": "string"
      },
      "type": "array",
      "description": "relevant tags for article"
    },
    "authors": {
      "items": {
        "properties": {
          "name": {
            "type": "string"
          },
          "email": {
            "type": "string"
          }
        },
        "type": "object",
        "required": ["name"]
      },
      "type": "array"
    }
  },
  "type": "object",
  "required": ["title", "date", "tags", "authors"]
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

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/dotprompt.go" region_tag="dot02" adjust_indentation="auto" %}
```

<!-- TODO: structured output unimplemented? -->

## Multi-message prompts

By default, Dotprompt constructs a single message with a `"user"` role. Some
prompts are best expressed as a combination of multiple messages, such as a
system prompt.

The `{% verbatim %}{{role}}{% endverbatim %}` helper provides a simple way to construct multi-message prompts:

```none
{% verbatim %}---
model: vertexai/gemini-1.5-flash
input:
  schema:
    userQuestion: string
---

{{role "system"}}
You are a helpful AI assistant that really loves to talk about food. Try to work
food items into all of your conversations.
{{role "user"}}
{{userQuestion}}{% endverbatim %}
```

<!-- TODO: Multi-Turn Prompts and History unimplemented? -->

## Multi-modal prompts

For models that support multimodal input such as images alongside text, you can
use the `{% verbatim %}{{media}}{% endverbatim %}` helper:

```none
{% verbatim %}---
model: vertexai/gemini-1.5-flash
input:
  schema:
    photoUrl: string
---

Describe this image in a detailed paragraph:

{{media url=photoUrl}}{% endverbatim %}
```

The URL can be `https://` or base64-encoded `data:` URIs for "inline" image
usage. In code, this would be:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/dotprompt.go" region_tag="dot03" adjust_indentation="auto" %}
```

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
- `my_prompt.geminipro.prompt`: a variant named "geminipro"

To use a prompt variant, specify the variant when loading:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/dotprompt.go" region_tag="dot04" adjust_indentation="auto" %}
```

The prompt loader will attempt to load the variant of that name, and fall back
to the baseline if none exists. This means you can use conditional loading based
on whatever criteria makes sense for your application:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/dotprompt.go" region_tag="dot05" adjust_indentation="auto" %}
```

The name of the variant is included in the metadata of generation traces, so you
can compare and contrast actual performance between variants in the Genkit trace
inspector.

<!-- TODO: Alternate ways to load and define prompts -->
