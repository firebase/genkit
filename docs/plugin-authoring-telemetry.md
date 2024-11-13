# Writing a Genkit Telemetry Plugin

[OpenTelemetry](http://opentelemetry.io) supports collecting traces, metrics, and logs. Firebase Genkit can be extended to export all telemetry data to any OpenTelemetry capable system by writing a telemetry plugin that configures the
[Node.js](https://opentelemetry.io/docs/languages/js/getting-started/nodejs/)
SDK.

## Configuration

Begin by exporting a function to configure and enable OpenTelemetry export.
This provides the entry point for consumers of your plugin. If your plugin 
is exclusively for telemetry and does not provide any Genkit actions, then
it's not necessary to install it in the Genkit configuration like other plugins.

```ts
import { enableTelemetry } from 'genkit/tracing';
import { logger } from 'genkit/logging';

export function enableMyTelemetry() {
  logger.init(getMyLogger()));
  return enableTelemetry(getMyTelemetry());
}
```

Calling Genkit's `enableTelemetry()` method registers your exporter for metrics and traces. 
A logger is registered by calling Genkit's `logger.init()` function.

This separation is currently necessary because logging functionality for Node.js
OpenTelemetry SDK is still [under development](https://opentelemetry.io/docs/languages/js/getting-started/nodejs/).
Logging is provided separately so that a plugin can explicitly control where the data is
written.


### Instrumentation

To control the export of traces and metrics, your plugin must call `enableTelemetry()` 
with an object that conforms to the OpenTelemetry `NodeSDKConfiguration` interface.
Genkit provides the `TelemetryConfig` type which is an alias for `Partial<NodeSDKConfiguration>`.

This configuration will be used by the Genkit framework to start up the
[`NodeSDK`](https://open-telemetry.github.io/opentelemetry-js/classes/_opentelemetry_sdk_node.NodeSDK.html).
This gives the plugin complete control of how the OpenTelemetry integration is used
by Genkit.

For example, the following telemetry config provides a simple in-memory trace and metric exporter:

```ts
import { AggregationTemporality, InMemoryMetricExporter, MetricReader, PeriodicExportingMetricReader } from '@opentelemetry/sdk-metrics';
import { AlwaysOnSampler, BatchSpanProcessor, InMemorySpanExporter } from '@opentelemetry/sdk-trace-base';
import { Resource } from '@opentelemetry/resources';
import { TelemetryConfig } from '@genkit-ai/core';

...

const myTelemetryConfig: TelemetryConfig = {
  resource: new Resource({}),
  spanProcessor: new BatchSpanProcessor(new InMemorySpanExporter()),
  sampler: new AlwaysOnSampler(),
  instrumentations: myPluginInstrumentations,
  metricReader: new PeriodicExportingMetricReader({
    exporter: new InMemoryMetricExporter(AggregationTemporality.CUMULATIVE),
  }),
};

```

### Logger

To control the logger used by the Genkit framework to write structured log data,
the plugin must call Genkit's `logger.init()` function with an object that conforms to the
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
import { logger } from 'genkit/logging';
import * as winston from 'winston';

...

logger.init(
  winston.createLogger({
    transports: [new winston.transports.Console()],
    format: winston.format.printf((info): string => {
      return `[${info.level}] ${info.message}`;
    }),
  }));
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
initialized. For example, the above example can be modified to import winston
when the logger is initialized.

## Full Example

The following is a full example of the telemetry plugin created above. For
a real world example, take a look at the `@genkit-ai/google-cloud` plugin.

```ts
import { genkitPlugin, GenkitPlugin } from 'genkit/plugin';
import {
  LoggerConfig,
  TelemetryConfig,
} from '@genkit-ai/core';
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
import {
  AlwaysOnSampler,
  BatchSpanProcessor,
  InMemorySpanExporter,
} from '@opentelemetry/sdk-trace-base';
import { getCurrentEnv } from 'genkit';
import { logger } from 'genkit/logging';
import { enableTelemetry } from 'genkit/tracing';

export interface MyPluginOptions {
  // [Optional] Your plugin options
}

export async function enableMyPlugin(options?: MyPluginOptions) {
  logger.init(await getLogger(getCurrentEnv()));
  return enableTelemetry(myTelemetryConfig);
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
  resource: new Resource({}),
  spanProcessor: new BatchSpanProcessor(new InMemorySpanExporter()),
  sampler: new AlwaysOnSampler(),
  instrumentations: myPluginInstrumentations,
  metricReader: new PeriodicExportingMetricReader({
    exporter: new InMemoryMetricExporter(AggregationTemporality.CUMULATIVE),
  }),
};

async function getLogger(env?: string) {
  // Controlling import order to allow OT to register telemetry
  // before importing winston.
  const winston = await import('winston');

  return winston.createLogger({
    transports: [new winston.transports.Console()],
    format: winston.format.printf((info): string => {
      return `[${info.level}] ${info.message}`;
    }),
  });
}

export const myPlugin: GenkitPlugin<[MyPluginOptions] | []> = genkitPlugin(
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
