# Writing a Genkit telemetry plugin

The Genkit libraries are instrumented with [OpenTelemetry](http://opentelemetry.io)
to support collecting traces, metrics, and logs. Genkit users can export this
telemetry data to monitoring and visualization tools by installing a plugin that
configures the [OpenTelemetry Go SDK](https://opentelemetry.io/docs/languages/go/getting-started/)
to export to a particular OpenTelemetry-capable system.

Genkit includes a plugin that configures OpenTelemetry to export data to
[Google Cloud Monitoring and Cloud Logging](plugins/google-cloud). To support
other monitoring systems, you can extend Genkit by writing a telemetry plugin,
as described on this page.

## Before you begin

Read [Writing Genkit plugins](plugin-authoring) for information about writing
any kind of Genkit plugin, including telemetry plugins. In particular, note that
every plugin must export an `Init` function, which users are expected to call
before using the plugin.

## Exporters and Loggers

As stated earlier, the primary job of a telemetry plugin is to configure
OpenTelemetry (which Genkit has already been instrumented with) to export data
to a particular service. To do so, you need the following:

- An implementation of OpenTelemetry's [`SpanExporter`](https://pkg.go.dev/go.opentelemetry.io/otel/sdk/trace#SpanExporter)
  interface that exports data to the service of your choice.
- An implementation of OpenTelemetry's [`metric.Exporter`](https://pkg.go.dev/go.opentelemetry.io/otel/sdk/metric#Exporter)
  interface that exports data to the service of your choice.
- Either a [`slog.Logger`](https://pkg.go.dev/log/slog#Logger)
  or an implementation of the [`slog.Handler`](https://pkg.go.dev/log/slog#Handler)
  interface, that exports logs to the service of your choice.

Depending on the service you're interested in exporting to, this might be a
relatively minor effort or a large one.

Because OpenTelemetry is an industry standard, many monitoring services already
have libraries that implement these interfaces. For example, the `googlecloud`
plugin for Genkit makes use of the
[`opentelemetry-operations-go`](https://github.com/GoogleCloudPlatform/opentelemetry-operations-go)
library, maintained by the Google Cloud team.
Similarly, many monitoring services provide libraries that implement the
standard `slog` interfaces.

On the other hand, if no such libraries are available for your service,
implementing the necessary interfaces can be a substantial project.

Check the [OpenTelemetry registry](https://opentelemetry.io/ecosystem/registry/?component=exporter&language=go)
or the monitoring service's docs to see if integrations are already available.

If you need to build these integrations yourself, take a look at the source of
the [official OpenTelemetry exporters](https://github.com/open-telemetry/opentelemetry-go/tree/main/exporters)
and the page [A Guide to Writing `slog` Handlers](https://github.com/golang/example/blob/master/slog-handler-guide/README.md).

## Building the plugin

### Dependencies

Every telemetry plugin needs to import the Genkit core library and several
OpenTelemetry libraries:

```golang
import {
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/telemetryplugin/telemetryplugin.go" region_tag="import" %}
}
```

If you are building a plugin around an existing OpenTelemetry or `slog`
integration, you will also need to import them.

### `Config`

A telemetry plugin should, at a minimum, support the following configuration
options:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/telemetryplugin/telemetryplugin.go" region_tag="config" adjust_indentation="auto" %}
```

The examples that follow assume you are making these options available and will
provide some guidance on how to handle them.

Most plugins will also include configuration settings for the service it's
exporting to (API key, project name, and so on).

### `Init()`

The `Init()` function of a telemetry plugin should do all of the following:

- Return early if Genkit is running in a development environment (such as when
  running with with `genkit start`) and the `Config.ForceExport` option isn't
  set:

  ```golang
  {% includecode github_path="firebase/genkit/go/internal/doc-snippets/telemetryplugin/telemetryplugin.go" region_tag="shouldexport" adjust_indentation="auto" %}
  ```

- Initialize your trace span exporter and register it with Genkit:

  ```golang
  {% includecode github_path="firebase/genkit/go/internal/doc-snippets/telemetryplugin/telemetryplugin.go" region_tag="registerspanexporter" adjust_indentation="auto" %}
  ```

- Initialize your metric exporter and register it with the OpenTelemetry
  library:

  ```golang
  {% includecode github_path="firebase/genkit/go/internal/doc-snippets/telemetryplugin/telemetryplugin.go" region_tag="registermetricexporter" adjust_indentation="auto" %}
  ```

  Use the user-configured collection interval (`Config.MetricInterval`) when
  initializing the `PeriodicReader`.

- Register your `slog` handler as the default logger:

  ```golang
  {% includecode github_path="firebase/genkit/go/internal/doc-snippets/telemetryplugin/telemetryplugin.go" region_tag="registerlogexporter" adjust_indentation="auto" %}
  ```

  You should configure your handler to honor the user-specified minimum log
  level (`Config.LogLevel`).

### PII redaction

Because most generative AI flows begin with user input of some kind, it's a
likely possibility that some flow traces contain personally-identifiable
information (PII). To protect your users' information, you should redact PII
from traces before you export them.

If you are building your own span exporter, you can build this functionality
into it.

If you're building your plugin around an existing OpenTelemetry integration, you
can wrap the provided span exporter with a custom exporter that carries out this
task. For example, the `googlecloud` plugin removes the `genkit:input` and
`genkit:output` attributes from every span before exporting them using a wrapper
similar to the following:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/telemetryplugin/exporters.go" region_tag="redactpii" adjust_indentation="auto" %}
```

## Troubleshooting

If you're having trouble getting data to show up where you expect, OpenTelemetry
provides a useful [diagnostic tool](https://opentelemetry.io/docs/languages/js/getting-started/nodejs/#troubleshooting)
that helps locate the source of the problem.
