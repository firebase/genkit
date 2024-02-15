import { Resource } from '@opentelemetry/resources';
import { GcpDetectorSync } from '@google-cloud/opentelemetry-resource-util';
import { MeterProvider } from '@opentelemetry/sdk-metrics';

export const METRIC_NAME_PREFIX = 'genkit.';
export const METER_NAME = 'genkit';

export const meterProvider = new MeterProvider({
  // Create a resource. Fill the `service.*` attributes in with real values for your service.
  // GcpDetectorSync will add in resource information about the current environment if you are
  // running on GCP. These resource attributes will be translated to a specific GCP monitored
  // resource if running on GCP. Otherwise, metrics will be sent with monitored resource
  // `generic_task`.
  resource: new Resource({}).merge(new GcpDetectorSync().detect()),
});
