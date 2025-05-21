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

### Before you begin {:#before-you-begin}

If you want to run the code examples on this page, first complete the steps in
the [Getting started](get-started) guide. All of the examples assume that you
have already installed Genkit as a dependency in your project.

### Models supported by Genkit {:#models-supported}

Genkit is designed to be flexible enough to use potentially any generative AI
model service. Its core libraries define the common interface for working with
models, and model plugins define the implementation details for working with a
specific model and its API.

The Genkit team maintains plugins for working with models provided by Vertex AI,
Google Generative AI, and Ollama:

- Gemini family of LLMs, through the
  [Google Cloud Vertex AI plugin](plugins/vertex-ai.md)
- Gemini family of LLMs, through the [Google AI plugin](plugins/google-genai.md)
- Imagen2 and Imagen3 image generation models, through Google Cloud Vertex AI
- Anthropic's Claude 3 family of LLMs, through Google Cloud Vertex AI's model
  garden
- Gemma 2, Llama 3, and many more open models, through the [Ollama
  plugin](plugins/ollama.md) (you must host the Ollama server yourself)

In addition, there are also several community-supported plugins that provide
interfaces to these models:

- Claude 3 family of LLMs, through the [Anthropic plugin](https://thefireco.github.io/genkit-plugins/docs/plugins/genkitx-anthropic){:.external}
- GPT family of LLMs through the [OpenAI plugin](https://thefireco.github.io/genkit-plugins/docs/plugins/genkitx-openai){:.external}
- GPT family of LLMs through the [Azure OpenAI plugin](https://thefireco.github.io/genkit-plugins/docs/plugins/genkitx-azure-openai){:.external}
- Command R family of LLMs through the [Cohere plugin](https://thefireco.github.io/genkit-plugins/docs/plugins/genkitx-cohere){:.external}
- Mistral family of LLMs through the [Mistral plugin](https://thefireco.github.io/genkit-plugins/docs/plugins/genkitx-mistral){:.external}
- Gemma 2, Llama 3, and many more open models hosted on Groq, through the
  [Groq plugin](https://thefireco.github.io/genkit-plugins/docs/plugins/genkitx-groq){:.external}

You can discover more by searching for [packages tagged with `genkit-model` on
npmjs.org](https://www.npmjs.com/search?q=keywords%3Agenkit-model){:.external}.

### Loading and configuring model plugins {:#loading-plugins}

Before you can use Genkit to start generating content, you need to load and
configure a model plugin. If you're coming from the Getting Started guide,
you've already done this. Otherwise, see the [Getting Started](get-started)
guide or the individual plugin's documentation and follow the steps there before
continuing.

### The generate() method {:#generate}

In Genkit, the primary interface through which you interact with generative AI
models is the `generate()` method.

The simplest `generate()` call specifies the model you want to use and a text
prompt:

```ts
{% includecode github_path="firebase/genkit/js/doc-snippets/src/models/minimal.ts" region_tag="minimal" adjust_indentation="auto" %}
```

When you run this brief example, it will print out some debugging information
followed by the output of the `generate()` call, which will usually be Markdown
text as in the following example:

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

```ts
{% includecode github_path="firebase/genkit/js/doc-snippets/src/models/index.ts" region_tag="ex01" adjust_indentation="auto" %}
```

This example uses a model reference exported by the model plugin. Another option
is to specify the model using a string identifier:

```ts
{% includecode github_path="firebase/genkit/js/doc-snippets/src/models/index.ts" region_tag="ex02" adjust_indentation="auto" %}
```

A model string identifier looks like `providerid/modelid`, where the provider ID
(in this case, `googleai`) identifies the plugin, and the model ID is a
plugin-specific string identifier for a specific version of a model.

Some model plugins, such as the Ollama plugin, provide access to potentially
dozens of different models and therefore do not export individual model
references. In these cases, you can only specify a model to `generate()` using
its string identifier.

These examples also illustrate an important point: when you use
`generate()` to make generative AI model calls, changing the model you want to
use is simply a matter of passing a different value to the model parameter. By
using `generate()` instead of the native model SDKs, you give yourself the
flexibility to more easily use several different models in your app and change
models in the future.

So far you have only seen examples of the simplest `generate()` calls. However,
`generate()` also provides an interface for more advanced interactions with
generative models, which you will see in the sections that follow.

### System prompts {:#system}

Some models support providing a _system prompt_, which gives the model
instructions as to how you want it to respond to messages from the user. You can
use the system prompt to specify a persona you want the model to adopt, the tone
of its responses, the format of its responses, and so on.

If the model you're using supports system prompts, you can provide one with the
`system` parameter:

```ts
{% includecode github_path="firebase/genkit/js/doc-snippets/src/models/index.ts" region_tag="ex03" adjust_indentation="auto" %}
```

### Model parameters {:#model-parameters}

The `generate()` function takes a `config` parameter, through which you can
specify optional settings that control how the model generates content:

```ts
{% includecode github_path="firebase/genkit/js/doc-snippets/src/models/index.ts" region_tag="ex04" adjust_indentation="auto" %}
```

The exact parameters that are supported depend on the individual model and model
API. However, the parameters in the previous example are common to almost every
model. The following is an explanation of these parameters:

#### Parameters that control output length

**maxOutputTokens**

LLMs operate on units called _tokens_. A token usually, but does not
necessarily, map to a specific sequence of characters. When you pass a prompt to
a model, one of the first steps it takes is to _tokenize_ your prompt string
into a sequence of tokens. Then, the LLM generates a sequence of tokens from the
tokenized input. Finally, the sequence of tokens gets converted back into text,
which is your output.

The maximum output tokens parameter simply sets a limit on how many tokens to
generate using the LLM. Every model potentially uses a different tokenizer, but
a good rule of thumb is to consider a single English word to be made of 2 to 4
tokens.

As stated earlier, some tokens might not map to character sequences. One such
example is that there is often a token that indicates the end of the sequence:
when an LLM generates this token, it stops generating more. Therefore, it's
possible and often the case that an LLM generates fewer tokens than the maximum
because it generated the "stop" token.

**stopSequences**

You can use this parameter to set the tokens or token sequences that, when
generated, indicate the end of LLM output. The correct values to use here
generally depend on how the model was trained, and are usually set by the model
plugin. However, if you have prompted the model to generate another stop
sequence, you might specify it here.

Note that you are specifying character sequences, and not tokens per se. In most
cases, you will specify a character sequence that the model's tokenizer maps to
a single token.

#### Parameters that control "creativity"

The _temperature_, _top-p_, and _top-k_ parameters together control how
"creative" you want the model to be. Below are very brief explanations of what
these parameters mean, but the more important point to take away is this: these
parameters are used to adjust the character of an LLM's output. The optimal
values for them depend on your goals and preferences, and are likely to be found
only through experimentation.

**temperature**

LLMs are fundamentally token-predicting machines. For a given sequence of tokens
(such as the prompt) an LLM predicts, for each token in its vocabulary, the
likelihood that the token comes next in the sequence. The temperature is a
scaling factor by which these predictions are divided before being normalized to
a probability between 0 and 1.

Low temperature values&mdash;between 0.0 and 1.0&mdash;amplify the difference in
likelihoods between tokens, with the result that the model will be even less
likely to produce a token it already evaluated to be unlikely. This is often
perceived as output that is less creative. Although 0.0 is technically not a
valid value, many models treat it as indicating that the model should behave
deterministically, and to only consider the single most likely token.

High temperature values&mdash;those greater than 1.0&mdash;compress the
differences in likelihoods between tokens, with the result that the model
becomes more likely to produce tokens it had previously evaluated to be
unlikely. This is often perceived as output that is more creative. Some model
APIs impose a maximum temperature, often 2.0.

**topP**

_Top-p_ is a value between 0.0 and 1.0 that controls the number of possible
tokens you want the model to consider, by specifying the cumulative probability
of the tokens. For example, a value of 1.0 means to consider every possible
token (but still take into account the probability of each token). A value of
0.4 means to only consider the most likely tokens, whose probabilities add up to
0.4, and to exclude the remaining tokens from consideration.

**topK**

_Top-k_ is an integer value that also controls the number of possible tokens you
want the model to consider, but this time by explicitly specifying the maximum
number of tokens. Specifying a value of 1 means that the model should behave
deterministically.

#### Experiment with model parameters

You can experiment with the effect of these parameters on the output generated
by different model and prompt combinations by using the Developer UI. Start the
developer UI with the `genkit start` command and it will automatically load all
of the models defined by the plugins configured in your project. You can quickly
try different prompts and configuration values without having to repeatedly make
these changes in code.

### Structured output {:#structured-output}

When using generative AI as a component in your application, you often want
output in a format other than plain text. Even if you're just generating content
to display to the user, you can benefit from structured output simply for the
purpose of presenting it more attractively to the user. But for more advanced
applications of generative AI, such as programmatic use of the model's output,
or feeding the output of one model into another, structured output is a must.

In Genkit, you can request structured output from a model by specifying a schema
when you call `generate()`:

```ts
{% includecode github_path="firebase/genkit/js/doc-snippets/src/models/index.ts" region_tag="importZod" adjust_indentation="auto" %}
```

```ts
{% includecode github_path="firebase/genkit/js/doc-snippets/src/models/index.ts" region_tag="ex05" adjust_indentation="auto" %}
```

Model output schemas are specified using the [Zod](https://zod.dev/){:.external}
library. In addition to a schema definition language, Zod also provides runtime
type checking, which bridges the gap between static TypeScript types and the
unpredictable output of generative AI models. Zod lets you write code that can
rely on the fact that a successful generate call will always return output that
conforms to your TypeScript types.

When you specify a schema in `generate()`, Genkit does several things behind the
scenes:

- Augments the prompt with additional guidance about the desired output format.
  This also has the side effect of specifying to the model what content exactly
  you want to generate (for example, not only suggest a menu item but also
  generate a description, a list of allergens, and so on).
- Parses the model output into a JavaScript object.
- Verifies that the output conforms with the schema.

To get structured output from a successful generate call, use the response
object's `output` property:

```ts
{% includecode github_path="firebase/genkit/js/doc-snippets/src/models/index.ts" region_tag="ex06" adjust_indentation="auto" %}
```

#### Handling errors

Note in the prior example that the `output` property can be `null`. This can
happen when the model fails to generate output that conforms to the schema.
The best strategy for dealing with such errors will depend on your exact use
case, but here are some general hints:

- **Try a different model**. For structured output to succeed, the model must be
  capable of generating output in JSON. The most powerful LLMs, like Gemini and
  Claude, are versatile enough to do this; however, smaller models, such as some
  of the local models you would use with Ollama, might not be able to generate
  structured output reliably unless they have been specifically trained to do
  so.

- **Make use of Zod's coercion abilities**: You can specify in your schemas that
  Zod should try to coerce non-conforming types into the type specified by the
  schema. If your schema includes primitive types other than strings, using Zod
  coercion can reduce the number of `generate()` failures you experience. The
  following version of `MenuItemSchema` uses type coercion to automatically
  correct situations where the model generates calorie information as a string
  instead of a number:

  ```ts
  {% includecode github_path="firebase/genkit/js/doc-snippets/src/models/index.ts" region_tag="ex07" adjust_indentation="auto" %}
  ```

- **Retry the generate() call**. If the model you've chosen only rarely fails to
  generate conformant output, you can treat the error as you would treat a
  network error, and simply retry the request using some kind of incremental
  back-off strategy.

### Streaming {:#streaming}

When generating large amounts of text, you can improve the experience for your
users by presenting the output as it's generated&mdash;streaming the output. A
familiar example of streaming in action can be seen in most LLM chat apps: users
can read the model's response to their message as it's being generated, which
improves the perceived responsiveness of the application and enhances the
illusion of chatting with an intelligent counterpart.

In Genkit, you can stream output using the `generateStream()` method. Its
syntax is similar to the `generate()` method:

```ts
{% includecode github_path="firebase/genkit/js/doc-snippets/src/models/index.ts" region_tag="ex08" adjust_indentation="auto" %}
```

The response object has a `stream` property, which you can use to iterate over
the streaming output of the request as it's generated:

```ts
{% includecode github_path="firebase/genkit/js/doc-snippets/src/models/index.ts" region_tag="ex09" adjust_indentation="auto" %}
```

You can also get the complete output of the request, as you can with a
non-streaming request:

```ts
{% includecode github_path="firebase/genkit/js/doc-snippets/src/models/index.ts" region_tag="ex10" adjust_indentation="auto" %}
```

Streaming also works with structured output:

```ts
{% includecode github_path="firebase/genkit/js/doc-snippets/src/models/index.ts" region_tag="ex11" adjust_indentation="auto" %}
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

### Multimodal input {:#multimodal-input}

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

```ts
{% includecode github_path="firebase/genkit/js/doc-snippets/src/models/index.ts" region_tag="ex12" adjust_indentation="auto" %}
```

In the above example, you specified an image using a publicly-accessible HTTPS
URL. You can also pass media data directly by encoding it as a data URL. For
example:

```ts
{% includecode github_path="firebase/genkit/js/doc-snippets/src/models/index.ts" region_tag="importReadFileAsync" adjust_indentation="auto" %}
```

```ts
{% includecode github_path="firebase/genkit/js/doc-snippets/src/models/index.ts" region_tag="ex13" adjust_indentation="auto" %}
```

All models that support media input support both data URLs and HTTPS URLs. Some
model plugins add support for other media sources. For example, the Vertex AI
plugin also lets you use Cloud Storage (`gs://`) URLs.

### Generating media {:#generating-media}

So far, most of the examples on this page have dealt with generating text using
LLMs. However, Genkit can also be used with image generation models. Using
`generate()` with an image generation model is similar to using an LLM. For
example, to generate an image using the Imagen2 model through Vertex AI:

1.  Genkit uses `data:` URLs as the standard output format for generated media.
    This is a standard format with many libraries available to handle them. This
    example uses the `data-urls` package from `jsdom`:

    ```posix-terminal
    npm i --save data-urls

    npm i --save-dev @types/data-urls
    ```

1.  To generate an image and save it to a file, call `generate()`, specifying an
    image generation model and the media type of output format:

    ```ts
    {% includecode github_path="firebase/genkit/js/doc-snippets/src/models/imagen.ts" region_tag="imagen" adjust_indentation="auto" %}
    ```

### Next steps {:#next-steps}

#### Learn more about Genkit

- As an app developer, the primary way you influence the output of generative AI
  models is through prompting. Read [Prompt management](dotpronpt) to learn how
  Genkit helps you develop effective prompts and manage them in your codebase.
- Although `generate()` is the nucleus of every generative AI powered
  application, real-world applications usually require additional work before
  and after invoking a generative AI model. To reflect this, Genkit introduces
  the concept of _flows_, which are defined like functions but add additional
  features such as observability and simplified deployment. To learn more, see
  [Defining workflows](flows).

#### Advanced LLM use

<!--

TODO: Add these when new pages are written.

- Many of your users will have interacted with large language models for the first time through chatbots. Although LLMs are capable of much more than simulating conversations, it remains a familiar and useful style of interaction. Even when your users will not be interacting directly with the model in this way, the conversational style of prompting is a powerful way to influence the output generated by an AI model. Read [Multi-turn chats][2] to learn how to use Genkit as part of an LLM chat implementation.

-->

- One way to enhance the capabilities of LLMs is to prompt them with a list of
  ways they can request more information from you, or request you to perform
  some action. This is known as _tool calling_ or _function calling_. Models
  that are trained to support this capability can respond to a prompt with a
  specially-formatted response, which indicates to the calling application that
  it should perform some action and send the result back to the LLM along with
  the original prompt. Genkit has library functions that automate both the
  prompt generation and the call-response loop elements of a tool calling
  implementation. See [Tool calling](tool-calling) to learn more.
- Retrieval-augmented generation (RAG) is a technique used to introduce
  domain-specific information into a model's output. This is accomplished by
  inserting relevant information into a prompt before passing it on to the
  language model. A complete RAG implementation requires you to bring several
  technologies together: text embedding generation models, vector databases, and
  large language models. See [Retrieval-augmented generation (RAG)](rag) to
  learn how Genkit simplifies the process of coordinating these various
  elements.

#### Testing model output

As a software engineer, you're used to deterministic systems where the same
input always produces the same output. However, with AI models being
probabilistic, the output can vary based on subtle nuances in the input, the
model's training data, and even randomness deliberately introduced by parameters
like temperature.

Genkit's evaluators are structured ways to assess the quality of your LLM's
responses, using a variety of strategies. Read more on the
[Evaluation](evaluation) page.
