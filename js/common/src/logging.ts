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
