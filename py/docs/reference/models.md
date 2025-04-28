# Generating content with AI models

At the heart of generative AI are AI _models_. Currently, the two most prominent
examples of generative models are large language models (LLMs) and image
generation models. These models take input, called a _prompt_ (most commonly
text, an image, or a combination of both), and from it produce as output text,
an image, or even audio or video.

The output of these models can be surprisingly convincing: LLMs generate text
that appears as though it could have been written by a human being, and image
generation models can produce images that are very close to real photographs or
artwork created by humans.

In addition, LLMs have proven capable of tasks beyond simple text generation:

- Writing computer programs
- Planning subtasks that are required to complete a larger task
- Organizing unorganized data
- Understanding and extracting information data from a corpus of text
- Following and performing automated activities based on a text description of
  the activity

There are many models available to you, from several different providers. Each
model has its own strengths and weaknesses and one model might excel at one task
but perform less well at others. Apps making use of generative AI can often
benefit from using multiple different models depending on the task at hand.

As an app developer, you typically don't interact with generative AI
models directly, but rather through services available as web APIs.
Although these services often have similar functionality, they all provide them
through different and incompatible APIs. If you want to make use of multiple
model services, you have to use each of their proprietary SDKs, potentially
incompatible with each other. And if you want to upgrade from one model to the
newest and most capable one, you might have to build that integration all over
again.

Genkit addresses this challenge by providing a single interface that abstracts
away the details of accessing potentially any generative AI model service, with
several pre-built implementations already available. Building your AI-powered
app around Genkit simplifies the process of making your first generative AI call
and makes it equally easy to combine multiple models or swap one model for
another as new models emerge.

### Loading and configuring model plugins

Before you can use Genkit to start generating content, you need to load and
configure a model plugin. If you're coming from the Getting Started guide,
you've already done this. Otherwise, see the [Getting Started](../get-started.md)
guide or the individual plugin's documentation and follow the steps there before
continuing.

### The generate() method

In Genkit, the primary interface through which you interact with generative AI
models is the `generate()` method.

The simplest `generate()` call specifies the model you want to use and a text
prompt:

```py
import asyncio
from genkit.ai import Genkit
from genkit.plugins.google_genai import GoogleGenai

ai = Genkit(
    plugins=[GoogleGenai()],
    model='googleai/gemini-2.0-flash',
)

async def main() -> None:
    result = await ai.generate(
        prompt='Invent a menu item for a pirate themed restaurant.',
    )
    print(result.text)

ai.run_main(main())
```

When you run this brief example it will print out the output of the `generate()`
all, which will usually be Markdown text as in the following example:

```md
## The Blackheart's Bounty

**A hearty stew of slow-cooked beef, spiced with rum and molasses, served in a
hollowed-out cannonball with a side of crusty bread and a dollop of tangy
pineapple salsa.**

**Description:** This dish is a tribute to the hearty meals enjoyed by pirates
on the high seas. The beef is tender and flavorful, infused with the warm spices
of rum and molasses. The pineapple salsa adds a touch of sweetness and acidity,
balancing the richness of the stew. The cannonball serving vessel adds a fun and
thematic touch, making this dish a perfect choice for any pirate-themed
adventure.
```

Run the script again and you'll get a different output.

The preceding code sample sent the generation request to the default model,
which you specified when you configured the Genkit instance.

You can also specify a model for a single `generate()` call:

```py
result = await ai.generate(
    prompt='Invent a menu item for a pirate themed restaurant.',
    model='googleai/gemini-2.0-pro',
)
```

A model string identifier looks like `providerid/modelid`, where the provider ID
(in this case, `google_genai`) identifies the plugin, and the model ID is a
plugin-specific string identifier for a specific version of a model.


These examples also illustrate an important point: when you use
`generate()` to make generative AI model calls, changing the model you want to
use is simply a matter of passing a different value to the model parameter. By
using `generate()` instead of the native model SDKs, you give yourself the
flexibility to more easily use several different models in your app and change
models in the future.

So far you have only seen examples of the simplest `generate()` calls. However,
`generate()` also provides an interface for more advanced interactions with
generative models, which you will see in the sections that follow.

### System prompts

Some models support providing a _system prompt_, which gives the model
instructions as to how you want it to respond to messages from the user. You can
use the system prompt to specify a persona you want the model to adopt, the tone
of its responses, the format of its responses, and so on.

If the model you're using supports system prompts, you can provide one with the
`system` parameter:

```py
result = await ai.generate(
    system='You are a food industry marketing consultant.',
    prompt='Invent a menu item for a pirate themed restaurant.',
)
```

### Model parameters

The `generate()` function takes a `config` parameter, through which you can
specify optional settings that control how the model generates content:

```py
result = await ai.generate(
    prompt='Invent a menu item for a pirate themed restaurant.',
    config={
      'max_output_tokens': 400,
      'stop_sequences': ['<end>', '<fin>'],
      'temperature': 1.2,
      'top_p': 0.4,
      'top_k': 50,
    },
)
```

The exact parameters that are supported depend on the individual model and model
API. However, the parameters in the previous example are common to almost every
model. The following is an explanation of these parameters:


### Structured output

When using generative AI as a component in your application, you often want
output in a format other than plain text. Even if you're just generating content
to display to the user, you can benefit from structured output simply for the
purpose of presenting it more attractively to the user. But for more advanced
applications of generative AI, such as programmatic use of the model's output,
or feeding the output of one model into another, structured output is a must.

In Genkit, you can request structured output from a model by specifying a schema
when you call `generate()`:

```py
from pydantic import BaseModel

class MenuItemSchema(BaseModel):
    name: str
    description: str
    calories: int
    allergens: list[str]

result = await ai.generate(
    prompt='Invent a menu item for a pirate themed restaurant.',
    output_schema=MenuItemSchema,
)
```

Model output schemas are specified using the [Pydantic Models](https://docs.pydantic.dev/latest/concepts/models/). In addition to a schema definition language, Pydantic also provides runtime
type checking, which bridges the gap between static Python types and the
unpredictable output of generative AI models. Pydantic lets you write code that can
rely on the fact that a successful generate call will always return output that
conforms to your Python types.

When you specify a schema in `generate()`, Genkit does several things behind the
scenes:

- Augments the prompt with additional guidance about the desired output format.
  This also has the side effect of specifying to the model what content exactly
  you want to generate (for example, not only suggest a menu item but also
  generate a description, a list of allergens, and so on).
- Parses the model output into a Pydantic object.
- Verifies that the output conforms with the schema.

To get structured output from a successful generate call, use the response
object's `output` property:

```py
output = response.output
```

### Streaming

When generating large amounts of text, you can improve the experience for your
users by presenting the output as it's generated&mdash;streaming the output. A
familiar example of streaming in action can be seen in most LLM chat apps: users
can read the model's response to their message as it's being generated, which
improves the perceived responsiveness of the application and enhances the
illusion of chatting with an intelligent counterpart.

In Genkit, you can stream output using the `generateStream()` method. Its
syntax is similar to the `generate()` method:

```py
stream, response = ai.generate_stream(
  prompt='Suggest a complete menu for a pirate themed restaurant.',
)
```

The response object has a `stream` property, which you can use to iterate over
the streaming output of the request as it's generated:

```py
async for chunk in stream:
    print(chunk.text)
```

You can also get the complete output of the request, as you can with a
non-streaming request:

```py
complete_text = (await response).text
```

Streaming also works with structured output:

```py
class MenuItemSchema(BaseModel):
    name: str
    description: str
    calories: int
    allergens: list[str]

class MenuSchema(BaseModel):
    starters: list[MenuItemSchema]
    mains: list[MenuItemSchema]
    desserts: list[MenuItemSchema]

stream, response = ai.generate_stream(
    prompt='Invent a menu item for a pirate themed restaurant.',
    output_schema=MenuSchema,
)

async for chunk in stream:
    print(chunk.output)

print((await response).output)
```

Streaming structured output works a little differently from streaming text: the
`output` property of a response chunk is an object constructed from the
accumulation of the chunks that have been produced so far, rather than an object
representing a single chunk (which might not be valid on its own). **Every chunk
of structured output in a sense supersedes the chunk that came before it**.

For example, here's what the first five outputs from the prior example might
look like:

```none
null

{ starters: [ {} ] }

{
  starters: [ { name: "Captain's Treasure Chest", description: 'A' } ]
}

{
  starters: [
    {
      name: "Captain's Treasure Chest",
      description: 'A mix of spiced nuts, olives, and marinated cheese served in a treasure chest.',
      calories: 350
    }
  ]
}

{
  starters: [
    {
      name: "Captain's Treasure Chest",
      description: 'A mix of spiced nuts, olives, and marinated cheese served in a treasure chest.',
      calories: 350,
      allergens: [Array]
    },
    { name: 'Shipwreck Salad', description: 'Fresh' }
  ]
}
```

### Multimodal input

The examples you've seen so far have used text strings as model prompts. While
this remains the most common way to prompt generative AI models, many models can
also accept other media as prompts. Media prompts are most often used in
conjunction with text prompts that instruct the model to perform some operation
on the media, such as to caption an image or transcribe an audio recording.

The ability to accept media input and the types of media you can use are
completely dependent on the model and its API. For example, the Gemini 1.5
series of models can accept images, video, and audio as prompts.

To provide a media prompt to a model that supports it, instead of passing a
simple text prompt to `generate`, pass an array consisting of a media part and a
text part:

```py
result = await ai.generate(
    prompt=[
      Part(media={'url': 'https://example.com/photo.jpg'}),
      Part(text='Compose a poem about this image.'),
    ],
)
```

In the above example, you specified an image using a publicly-accessible HTTPS
URL. You can also pass media data directly by encoding it as a data URL. For
example:

```ts
base64_encoded_image = base64.b64encode(read_file('image.jpg'))
result = await ai.generate(
    prompt=[
      Part(media={'url': f'data:image/jpeg;base64,{base64_encoded_image}'}),
      Part(text='Compose a poem about this image.'),
    ],
)
```

All models that support media input support both data URLs and HTTPS URLs. Some
model plugins add support for other media sources. For example, the Vertex AI
plugin also lets you use Cloud Storage (`gs://`) URLs.

### Generating media {:#generating-media}

So far, most of the examples on this page have dealt with generating text using
LLMs. However, Genkit can also be used with image generation models. Using
`generate()` with an image generation model is similar to using an LLM. For
example, to generate an image using the Imagen model:

```py
TODO
```
