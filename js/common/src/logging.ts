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

import { pino } from 'pino';

const logger = pino({
  level: 'error',
  transport: {
    target: 'pino-pretty',
  },
});

/**
 * Sets logging level.
 */
export function setLogLevel(
  level: 'fatal' | 'error' | 'warn' | 'info' | 'debug' | 'trace'
) {
  logger.level = level;
}

export default {
  info: (...args: any) => {
    // eslint-disable-next-line prefer-spread
    logger.info.apply(logger, args);
  },
  debug: (...args: any) => {
    // eslint-disable-next-line prefer-spread
    logger.debug.apply(logger, args);
  },
  trace: (...args: any) => {
    // eslint-disable-next-line prefer-spread
    logger.trace.apply(logger, args);
  },
  error: (...args: any) => {
    // eslint-disable-next-line prefer-spread
    logger.error.apply(logger, args);
  },
  warn: (...args: any) => {
    // eslint-disable-next-line prefer-spread
    logger.warn.apply(logger, args);
  },
  fatal: (...args: any) => {
    // eslint-disable-next-line prefer-spread
    logger.fatal.apply(logger, args);
  },
};
