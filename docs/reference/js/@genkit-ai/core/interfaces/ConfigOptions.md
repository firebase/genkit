# Interface: ConfigOptions

## Properties

| Property | Type |
| :------ | :------ |
| `defaultModel?` | \{ `"config"`: `Record`\<`string`, `any`\>; `"name"`: `string` \| \{ `"name"`: `string`; \}; \} |
| `defaultModel.config?` | `Record`\<`string`, `any`\> |
| `defaultModel.name` | `string` \| \{ `"name"`: `string`; \} |
| `enableTracingAndMetrics?` | `boolean` |
| `flowStateStore?` | `string` |
| `logLevel?` | `"error"` \| `"debug"` \| `"info"` \| `"warn"` |
| `plugins?` | [`PluginProvider`](PluginProvider.md)[] |
| `promptDir?` | `string` |
| `telemetry?` | [`TelemetryOptions`](TelemetryOptions.md) |
| `traceStore?` | `string` |
