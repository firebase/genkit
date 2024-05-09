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

import { LoggerConfig } from './telemetryTypes.js';

const LOG_LEVELS = ['debug', 'info', 'warn', 'error'];

class Logger {
  logger: {
    debug(...args: any);
    info(...args: any);
    warn(...args: any);
    error(...args: any);
    level: string;
  };

  defaultLogger = {
    shouldLog(targetLevel: string) {
      return LOG_LEVELS.indexOf(this.level) <= LOG_LEVELS.indexOf(targetLevel);
    },
    debug(...args: any) {
      this.shouldLog('debug') && console.debug(...args);
    },
    info(...args: any) {
      this.shouldLog('info') && console.info(...args);
    },
    warn(...args: any) {
      this.shouldLog('warn') && console.warn(...args);
    },
    error(...args: any) {
      this.shouldLog('error') && console.error(...args);
    },
    level: 'info',
  };

  constructor() {
    this.logger = this.defaultLogger;
  }

  async init(config: LoggerConfig) {
    this.logger = await config.getLogger(process.env.GENKIT_ENV || 'prod');
  }

  info(...args: any) {
    // eslint-disable-next-line prefer-spread
    this.logger.info.apply(this.logger, args);
  }
  debug(...args: any) {
    // eslint-disable-next-line prefer-spread
    this.logger.debug.apply(this.logger, args);
  }
  error(...args: any) {
    // eslint-disable-next-line prefer-spread
    this.logger.error.apply(this.logger, args);
  }
  warn(...args: any) {
    // eslint-disable-next-line prefer-spread
    this.logger.warn.apply(this.logger, args);
  }

  setLogLevel(level: 'error' | 'warn' | 'info' | 'debug') {
    this.logger.level = level;
  }

  logStructured(msg: string, metadata: any) {
    this.logger.info(msg, metadata);
  }

  logStructuredError(msg: string, metadata: any) {
    this.logger.error(msg, metadata);
  }
}

export const logger = new Logger();
