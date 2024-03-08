import { Resource } from '@opentelemetry/resources';
import { GcpDetectorSync } from '@google-cloud/opentelemetry-resource-util';
import { MeterProvider } from '@opentelemetry/sdk-metrics';

export const METRIC_NAME_PREFIX = 'genkit.';
export const METER_NAME = 'genkit';
