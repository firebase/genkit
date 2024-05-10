# Interface: InitializedPlugin

## Properties

| Property | Type |
| :------ | :------ |
| `embedders?` | [`Action`](../type-aliases/Action.md)\<`ZodTypeAny`, `ZodTypeAny`, `Record`\<`string`, `any`\>\>[] |
| `evaluators?` | [`Action`](../type-aliases/Action.md)\<`ZodTypeAny`, `ZodTypeAny`, `Record`\<`string`, `any`\>\>[] |
| `flowStateStore?` | [`Provider`](Provider.md)\<[`FlowStateStore`](FlowStateStore.md)\> \| [`Provider`](Provider.md)\<[`FlowStateStore`](FlowStateStore.md)\>[] |
| `indexers?` | [`Action`](../type-aliases/Action.md)\<`ZodTypeAny`, `ZodTypeAny`, `Record`\<`string`, `any`\>\>[] |
| `models?` | [`Action`](../type-aliases/Action.md)\<`ZodTypeAny`, `ZodTypeAny`, `Record`\<`string`, `any`\>\>[] |
| `retrievers?` | [`Action`](../type-aliases/Action.md)\<`ZodTypeAny`, `ZodTypeAny`, `Record`\<`string`, `any`\>\>[] |
| `telemetry?` | \{ `"instrumentation"`: [`Provider`](Provider.md)\<[`TelemetryConfig`](TelemetryConfig.md)\>; `"logger"`: [`Provider`](Provider.md)\<[`LoggerConfig`](LoggerConfig.md)\>; \} |
| `telemetry.instrumentation?` | [`Provider`](Provider.md)\<[`TelemetryConfig`](TelemetryConfig.md)\> |
| `telemetry.logger?` | [`Provider`](Provider.md)\<[`LoggerConfig`](LoggerConfig.md)\> |
| `traceStore?` | [`Provider`](Provider.md)\<`TraceStore`\> \| [`Provider`](Provider.md)\<`TraceStore`\>[] |
