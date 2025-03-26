# Writing Genkit plugins

Genkit's capabilities are designed to be extended by plugins. Genkit
plugins are configurable modules that can provide models, retrievers, indexers,
trace stores, and more. You've already seen plugins in action just by using
Genkit:

```golang
import {
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/models.go" region_tag="import" %}
}
```

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/models.go" region_tag="init" adjust_indentation="auto" %}
```

The Vertex AI plugin takes configuration (such as the user's Google Cloud
project ID) and registers a variety of new models, embedders, and more with the
Genkit registry. The registry serves as a lookup service for named actions at
runtime, and powers Genkit's local UI for running and inspecting models,
prompts, and more.

## Creating a plugin

In Go, a Genkit plugin is simply a package that adheres to a small set of
conventions. A single module can contain several plugins.

### Provider ID

Every plugin must have a unique identifier string that distinguishes it from
other plugins. Genkit uses this identifier as a namespace for every resource
your plugin defines, to prevent naming conflicts with other plugins.

For example, if your plugin has an ID `yourplugin` and provides a model called
`text-generator`, the full model identifier will be `yourplugin/text-generator`.

You don't need to export your provider ID, but you should define it once for
your plugin and use it consistently when required by a Genkit function.

```golang
const providerID = "yourplugin"
```

### Standard exports

Every plugin should define and export the following symbols:

- An `Init()` function with a declaration like the following:

  ```golang
  func Init(ctx context.Context, cfg *Config) (err error)
  ```

  Omit any parameters you don't use (for example, you might not have a `cfg`
  parameter if your plugin does not provide any plugin-wide configuration
  options).

  In this function, perform any setup steps required by your plugin. For
  example:

  - Confirm that any required configuration values are specified and assign
    default values to any unspecified optional settings.
  - Verify that the given configuration options are valid together.
  - Create any shared resources required by the rest of your plugin. For
    example, create clients for any services your plugin accesses.

  To the extent possible, the resources provided by your plugin shouldn't
  assume that the user has taken any action other than calling `Init`.

  You should define and export this function even if your plugin doesn't require
  any initialization. In this case, `Init` can just return a `nil` error.

- A `Config` struct type. This type should encapsulate all of the configuration
  options accepted by `Init`.

  For any plugin options that are secret values, such as API keys, you should
  offer both a `Config` option and a default environment variable to configure
  it. This lets your plugin take advantage of the secret management features
  offered by many hosting providers (such as Cloud Secret Manager, which you can
  use with Cloud Run). For example:

  ```golang
  {% includecode github_path="firebase/genkit/go/internal/doc-snippets/plugin/plugin.go" region_tag="init" adjust_indentation="auto" %}
  ```

## Building plugin features

A single plugin can activate many new things within Genkit. For example, the
Vertex AI plugin activates several new models as well as an embedder.

### Model plugins

Genkit model plugins add one or more generative AI models to the Genkit
registry. A model represents any generative model that is capable of receiving a
prompt as input and generating text, media, or data as output.

See [Writing a Genkit model plugin](plugin-authoring-models).

### Telemetry plugins

Genkit telemetry plugins configure Genkit's OpenTelemetry instrumentation to
export traces, metrics, and logs to a particular monitoring or visualization
tool.

See [Writing a Genkit telemetry plugin](plugin-authoring-telemetry).

## Publishing a plugin

Genkit plugins can be published as normal Go packages. To increase
discoverability, your package should have `genkit` somewhere in its name so it
can be found with a simple search on
[`pkg.go.dev`](https://pkg.go.dev/search?q=genkit). Any of the following are
good choices:

- `github.com/yourorg/genkit-plugins/servicename`
- `github.com/yourorg/your-repo/genkit/servicename`
