# Interface: TelemetryOptions

Options for configuring the Open-Telemetry export configuration as part of a
Genkit config file.

## Properties

| Property | Type | Description |
| :------ | :------ | :------ |
| `instrumentation` | `string` | Specifies which telemetry export provider to use. The value specified here<br />must match the id of a {TelemetryConfig} provided by an installed plugin.<br /><br />Note: Telemetry data is only exported when running in the `prod`<br />environment. |
| `logger` | `string` | Specifies which winston logging provider to use. The value specified here<br />must match the id of a {TelemetryConfig} provided by an installed plugin. |
