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

import * as winston from 'winston';
import { LoggerConfig } from './telemetryTypes';

class Logger {
  readonly genkitLabels = { labels: { module: 'genkit' } };

  textLogger: winston.Logger;
  structuredLogger: winston.Logger;

  constructor() {
    this.textLogger = winston.createLogger({
      transports: [new winston.transports.Console()],
      level: 'debug',
      ...this.getDevConfigurationOverrides(),
    });
    this.structuredLogger = winston.createLogger({
      transports: [],
      level: 'info',
    });
  }

  private getDevConfigurationOverrides() {
    return process.env.GENKIT_ENV === 'dev'
      ? {
          format: winston.format.printf((info): string => {
            return `[${info.level}] ${info.message}`;
          }),
        }
      : {};
  }

  init(config: LoggerConfig) {
    this.textLogger = winston.createLogger({
      ...config.getConfig(),
      ...this.getDevConfigurationOverrides(),
    });
    this.structuredLogger = winston.createLogger({
      ...config.getConfig(),
      level: 'info',
      format: winston.format.json(),
    });
  }

  info(...args: any) {
    // eslint-disable-next-line prefer-spread
    this.textLogger.info(args, this.genkitLabels);
  }
  debug(...args: any) {
    // eslint-disable-next-line prefer-spread
    this.textLogger.debug(args, this.genkitLabels);
  }
  error(...args: any) {
    // eslint-disable-next-line prefer-spread
    this.textLogger.error(args, this.genkitLabels);
  }
  warn(...args: any) {
    // eslint-disable-next-line prefer-spread
    this.textLogger.warn(args, this.genkitLabels);
  }

  setLogLevel(level: 'error' | 'warn' | 'info' | 'debug') {
    this.textLogger.level = level;
  }

  logStructured(obj: any) {
    this.structuredLogger.info(obj);
  }
}

export const logger = new Logger();
