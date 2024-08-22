# Writing a Genkit Telemetry Plugin

[OpenTelemetry](http://opentelemetry.io) supports collecting traces, metrics, and logs. Firebase Genkit can be extended to export all telemetry data to any OpenTelemetry capable system by writing a telemetry plugin that configures the
[Node.js](https://opentelemetry.io/docs/languages/js/getting-started/nodejs/)
SDK.

Note: Telemetry configuration can be provided by any plugin. Follow the steps described
in the [Writing Genkit plugins](./plugin-authoring.md#creating-a-plugin) guide if you are authoring a new plugin.

## Configuration

To control telemetry export, your plugin's `PluginOptions` must provide a
`telemetry` object that conforms to the `telemetry` block in Genkit's configuration.

```ts
export interface InitializedPlugin {
  ...
  telemetry?: {
    instrumentation?: Provider<TelemetryConfig>;
    logger?: Provider<LoggerConfig>;
  };
}
```

This object can provide two separate configurations:

- `instrumentation`: provides OpenTelemetry configuration for `Traces` and
  `Metrics`.
- `logger`: provides the underlying logger used by Genkit for writing
  structured log data including inputs and outputs of Genkit flows.

This separation is currently necessary because logging functionality for Node.js
OpenTelemetry SDK is still [under development](https://opentelemetry.io/docs/languages/js/getting-started/nodejs/).
Logging is provided separately so that a plugin can control where the data is
written explicitly.

```ts
import { genkitPlugin, Plugin } from '@genkit/core';

...

export interface MyPluginOptions {
  // [Optional] Your plugin options
}

export const myPlugin: Plugin<[MyPluginOptions] | []> = genkitPlugin(
  'myPlugin',
  async (options?: MyPluginOptions) => {
    return {
      telemetry: {
        instrumentation: {
          id: 'myPlugin',
          value: myTelemetryConfig,
        },
        logger: {
          id: 'myPlugin',
          value: myLogger,
        },
      },
    };
  }
);

export default myPlugin;
```

With the above code block, your plugin will now provide Genkit with a telemetry
congiguration that can be used by developers.

### Instrumentation

To control the export of traces and metrics, your plugin must provide an
`instrumentation` property on the `telemetry` object that conforms to the
`TelemetryConfig` interface:

```ts
interface TelemetryConfig {
  getConfig(): Partial<NodeSDKConfiguration>;
}
```

This provides a `Partial<NodeSDKConfiguration>` which will be used by the
Genkit framework to start up the
[`NodeSDK`](https://open-telemetry.github.io/opentelemetry-js/classes/_opentelemetry_sdk_node.NodeSDK.html).
This gives the plugin complete control of how the OpenTelemetry integration is used
by Genkit.

For example, the following telemetry config provides a simple in-memory trace and metric exporter:

```ts
import { AggregationTemporality, InMemoryMetricExporter, MetricReader, PeriodicExportingMetricReader } from '@opentelemetry/sdk-metrics';
import { AlwaysOnSampler, BatchSpanProcessor, InMemorySpanExporter } from '@opentelemetry/sdk-trace-base';
import { NodeSDKConfiguration } from '@opentelemetry/sdk-node';
import { Resource } from '@opentelemetry/resources';
import { TelemetryConfig } from '@genkit/core';

...

const myTelemetryConfig: TelemetryConfig = {
  getConfig(): Partial<NodeSDKConfiguration> {
    return {
      resource: new Resource({}),
      spanProcessor: new BatchSpanProcessor(new InMemorySpanExporter()),
      sampler: new AlwaysOnSampler(),
      instrumentations: myPluginInstrumentations,
      metricReader: new PeriodicExportingMetricReader({
        exporter: new InMemoryMetricExporter(AggregationTemporality.CUMULATIVE),
      }),
    };
  },
};

```

### Logger

To control the logger used by the Genkit framework to write structured log data,
the plugin must provide a `logger` property on the `telemetry` object that conforms to the
`LoggerConfig` interface:

```ts
interface LoggerConfig {
  getLogger(env: string): any;
}
```

Note: Although the type is specified as an `any`, the object must conform to the log4j standard outlined below.

```ts
{
  debug(...args: any);
  info(...args: any);
  warn(...args: any);
  error(...args: any);
  level: string;
}
```

Most popular logging frameworks conform to this. One such framework is
[winston](https://github.com/winstonjs/winston), which allows for configuring
transporters that can directly push the log data to a location of your choosing.

For example, to provide a winston logger that writes log data to the console,
you can update your plugin logger to use the following:

```ts
import * as winston from 'winston';

...

const myLogger: LoggerConfig = {
  getLogger(env: string) {
    return winston.createLogger({
      transports: [new winston.transports.Console()],
      format: winston.format.printf((info): string => {
        return `[${info.level}] ${info.message}`;
      }),
    });
  }
};
```

## Linking logs and Traces

Often it is desirable to have your log statements correlated with the
OpenTelemetry traces exported by your plugin. Because the log statements are not
exported by the OpenTelemetry framework directly this doesn't happen out of the
box. Fortunately, OpenTelemetry supports instrumentations that will copy trace
and span IDs onto log statements for popular logging frameworks like [winston]()
and [pino](). By using the `@opentelemetry/auto-instrumentations-node` package,
you can have these (and other) instrumentations configured automatically, but in
some cases you may need to control the field names and values for traces and
spans. To do this, you'll need to provide a custom LogHook instrumentation to
the NodeSDK configuration provided by your `TelemetryConfig`:

```ts
import { Instrumentation } from '@opentelemetry/instrumentation';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';
import { WinstonInstrumentation } from '@opentelemetry/instrumentation-winston';
import { Span } from '@opentelemetry/api';

const myPluginInstrumentations: Instrumentation[] =
  getNodeAutoInstrumentations().concat([
    new WinstonInstrumentation({
      logHook: (span: Span, record: any) => {
        record['my-trace-id'] = span.spanContext().traceId;
        record['my-span-id'] = span.spanContext().spanId;
        record['is-trace-sampled'] = span.spanContext().traceFlags;
      },
    }),
  ]);
```

The example enables all auto instrumentations for the OpenTelemetry `NodeSDK`,
and then provides a custom `WinstonInstrumentation` that writes the trace and
span IDs to custom fields on the log message.

Note: For log hook instrumentations to take effect, those instrumentations
_must_ be registered before the logging framework is imported.

The Genkit framework will guarantee that your plugin's `TelemetryConfig` will be
initialized before your plugin's `LoggerConfig`, but you must take care to
ensure that the underlying logger is not imported until the LoggerConfig is
initialized. For example, the above loggingConfig can be modified as follows:

```ts
const myLogger: LoggerConfig = {
  async getLogger(env: string) {
    // Do not import winston before calling getLogger so that the NodeSDK
    // instrumentations can be registered first.
    const winston = await import('winston');

    return winston.createLogger({
      transports: [new winston.transports.Console()],
      format: winston.format.printf((info): string => {
        return `[${info.level}] ${info.message}`;
      }),
    });
  },
};
```

## Full Example

The following is a full example of the telemetry plugin created above. For
a real world example, take a look at the `@genkit/google-cloud` plugin.

```ts
import {
  genkitPlugin,
  LoggerConfig,
  Plugin,
  TelemetryConfig,
} from '@genkit/core';
import { Span } from '@opentelemetry/api';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';
import { Instrumentation } from '@opentelemetry/instrumentation';
import { WinstonInstrumentation } from '@opentelemetry/instrumentation-winston';
import { Resource } from '@opentelemetry/resources';
import {
  AggregationTemporality,
  InMemoryMetricExporter,
  PeriodicExportingMetricReader,
} from '@opentelemetry/sdk-metrics';
import { NodeSDKConfiguration } from '@opentelemetry/sdk-node';
import {
  AlwaysOnSampler,
  BatchSpanProcessor,
  InMemorySpanExporter,
} from '@opentelemetry/sdk-trace-base';

export interface MyPluginOptions {
  // [Optional] Your plugin options
}

const myPluginInstrumentations: Instrumentation[] =
  getNodeAutoInstrumentations().concat([
    new WinstonInstrumentation({
      logHook: (span: Span, record: any) => {
        record['my-trace-id'] = span.spanContext().traceId;
        record['my-span-id'] = span.spanContext().spanId;
        record['is-trace-sampled'] = span.spanContext().traceFlags;
      },
    }),
  ]);

const myTelemetryConfig: TelemetryConfig = {
  getConfig(): Partial<NodeSDKConfiguration> {
    return {
      resource: new Resource({}),
      spanProcessor: new BatchSpanProcessor(new InMemorySpanExporter()),
      sampler: new AlwaysOnSampler(),
      instrumentations: myPluginInstrumentations,
      metricReader: new PeriodicExportingMetricReader({
        exporter: new InMemoryMetricExporter(AggregationTemporality.CUMULATIVE),
      }),
    };
  },
};

const myLogger: LoggerConfig = {
  async getLogger(env: string) {
    // Do not import winston before calling getLogger so that the NodeSDK
    // instrumentations can be registered first.
    const winston = await import('winston');

    return winston.createLogger({
      transports: [new winston.transports.Console()],
      format: winston.format.printf((info): string => {
        return `[${info.level}] ${info.message}`;
      }),
    });
  },
};

export const myPlugin: Plugin<[MyPluginOptions] | []> = genkitPlugin(
  'myPlugin',
  async (options?: MyPluginOptions) => {
    return {
      telemetry: {
        instrumentation: {
          id: 'myPlugin',
          value: myTelemetryConfig,
        },
        logger: {
          id: 'myPlugin',
          value: myLogger,
        },
      },
    };
  }
);

export default myPlugin;
```

## Troubleshooting

If you're having trouble getting data to show up where you expect, OpenTelemetry provides a useful
[Diagnostic tool](https://opentelemetry.io/docs/languages/js/getting-started/nodejs/#troubleshooting)
that helps locate the source of the problem.
