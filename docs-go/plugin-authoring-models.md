# Writing a Genkit model plugin

Genkit model plugins add one or more generative AI models to the Genkit
registry. A model represents any generative model that is capable of receiving a
prompt as input and generating text, media, or data as output.

## Before you begin

Read [Writing Genkit plugins](plugin-authoring) for information about writing
any kind of Genkit plug-in, including model plugins. In particular, note that
every plugin must export an `Init` function, which users are expected to call
before using the plugin.

## Model definitions

Generally, a model plugin will make one or more `ai.DefineModel` calls in its
`Init` function&mdash;once for each model the plugin is providing an interface
to.

A model definition consists of three components:

1.  Metadata declaring the model's capabilities.
2.  A configuration type with any specific parameters supported by the model.
3.  A generation function that accepts a `ai.GenerateRequest` and returns a
    `ai.GenerateResponse`, presumably using an AI model to generate the latter.

At a high level, here's what it looks like in code:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/plugin/plugin.go" region_tag="cfg" adjust_indentation="auto" %}
```

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/plugin/plugin.go" region_tag="definemodel" adjust_indentation="auto" %}
```

### Declaring model capabilities

Every model definition must contain, as part of its metadata, a
`ai.ModelCapabilities` value that declares which features the model supports.
Genkit uses this information to determine certain behaviors, such as verifying
whether certain inputs are valid for the model. For example, if the model
doesn't support multi-turn interactions, then it's an error to pass it a message
history.

Note that these declarations refer to the capabilities of the model as provided
by your plugin, and do not necessarily map one-to-one to the capabilities of the
underlying model and model API. For example, even if the model API doesn't
provide a specific way to define system messages, your plugin might still
declare support for the system role, and implement it as special logic that
inserts system messages into the user prompt.

### Defining your model's config schema {:#config-schema}

To specify the generation options a model supports, define and export a
configuration type. Genkit has a `ai.GenerationCommonConfig` type that contains
options frequently supported by generative AI model services, which you can
embed or use outright.

Your generation function should verify that the request contains the correct
options type.

### Transforming requests and responses

The generation function carries out the primary work of a Genkit model plugin:
transforming the `ai.GenerateRequest` from Genkit's common format into a format
that is supported by your model's API, and then transforming the response from
your model into the `ai.GenerateResponse` format used by Genkit.

Sometimes, this may require massaging or manipulating data to work around model
limitations. For example, if your model does not natively support a `system`
message, you may need to transform a prompt's system message into a user-model
message pair.

## Exports

In addition to the resources that all plugins must export&mdash;an `Init`
function and a `Config` type&mdash;a model plugin should also export the
following:

- A generation config type, as discussed [earlier](#config-schema).

- A `Model` function, which returns references to your plugin's defined models.
  Often, this can simply be:

  ```golang
  func Model(name string) *ai.Model {
      return ai.LookupModel(providerID, name)
  }
  ```

- **Optional**: A `DefineModel` function, which lets users define models that
  your plugin can provide, but that you do not automatically define. There are
  two main reasons why you might want to provide such a function:

  - Your plugin provides access to too many models to practically register each
    one. For example, the Ollama plugin can provide access to dozens of
    different models, with more added frequently. For this reason, it doesn't
    automatically define any models, and instead requires the user to call
    `DefineModel` for each model they want to use.

  - To give your users the ability to use newly-released models that you have
    not yet added to your plugin.

  A plugin's `DefineModel` function is typically a frontend to `ai.DefineModel`
  that defines a generation function, but lets the user specify the model name
  and model capabilities.
