/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { Counter, Histogram, Meter, metrics } from '@opentelemetry/api';

type MetricCreateFn<T> = (meter: Meter) => T;
export const METER_NAME = 'genkit';

/**
 * Wrapper for OpenTelemetry metrics.
 *
 * The OpenTelemetry {MeterProvider} can only be accessed through the metrics
 * API after the NodeSDK library has been initialized. To prevent race
 * conditions we defer the instantiation of the metric to when it is first
 * ticked.
 *
 * Note: This metric should only be used for writing metrics adhering to the
 * OpenTelemetry Generative AI Semantic Conventions. Any other metric should
 * be written by an appropriate plugin, eg. google-cloud plugin.
 *
 * https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-metrics/
 */
export class Metric<T> {
  readonly createFn: MetricCreateFn<T>;
  readonly meterName: string;
  metric?: T;

  constructor(createFn: MetricCreateFn<T>, meterName: string = METER_NAME) {
    this.meterName = meterName;
    this.createFn = createFn;
  }

  get(): T {
    if (!this.metric) {
      this.metric = this.createFn(
        metrics.getMeterProvider().getMeter(this.meterName)
      );
    }

    return this.metric;
  }
}

/**
 * Wrapper for an OpenTelemetry Counter.
 *
 * By using this wrapper, we defer initialization of the counter until it is
 * need, which ensures that the OpenTelemetry SDK has been initialized before
 * the metric has been defined.
 *
 * Note: This counter should only be used for writing metrics adhering to the
 * OpenTelemetry Generative AI Semantic Conventions. Any other metric should
 * be written by an appropriate plugin, eg. google-cloud plugin.
 *
 * https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-metrics/
 */
export class MetricCounter extends Metric<Counter> {
  constructor(name: string, options: any) {
    super((meter) => meter.createCounter(name, options));
  }

  add(val?: number, opts?: any) {
    if (val) {
      this.get().add(val, opts);
    }
  }
}

/**
 * Wrapper for an OpenTelemetry Histogram.
 *
 * By using this wrapper, we defer initialization of the counter until it is
 * need, which ensures that the OpenTelemetry SDK has been initialized before
 * the metric has been defined.
 *
 * Note: This histogram should only be used for writing metrics adhering to the
 * OpenTelemetry Generative AI Semantic Conventions. Any other metric should
 * be written by an appropriate plugin, eg. google-cloud plugin.
 *
 * https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-metrics/
 */
export class MetricHistogram extends Metric<Histogram> {
  constructor(name: string, options: any) {
    super((meter) => meter.createHistogram(name, options));
  }

  record(val?: number, opts?: any) {
    if (val) {
      this.get().record(val, opts);
    }
  }
}
