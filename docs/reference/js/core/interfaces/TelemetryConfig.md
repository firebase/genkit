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

[core/src/telemetryTypes.ts:25](https://github.com/firebase/genkit/blob/9cb10ef63dd6659f1a31ffd2367b7efa8acc10e5/js/core/src/telemetryTypes.ts#L25)
