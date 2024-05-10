# Interface: TelemetryConfig

Provides a {NodeSDKConfiguration} configuration for use with the
Open-Telemetry SDK. This configuration allows plugins to specify how and
where open telemetry data will be exported.

## Methods

### getConfig()

```ts
getConfig(): Partial<NodeSDKConfiguration>
```

#### Returns

`Partial`\<`NodeSDKConfiguration`\>

#### Source

[core/src/telemetryTypes.ts:25](https://github.com/firebase/genkit/blob/2b0be364306d92a8e7d13efc2da4fb04c1d21e29/js/core/src/telemetryTypes.ts#L25)
