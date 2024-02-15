import pino from 'pino';

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
    logger.info.apply(logger, args);
  },
  debug: (...args: any) => {
    logger.debug.apply(logger, args);
  },
  trace: (...args: any) => {
    logger.trace.apply(logger, args);
  },
  error: (...args: any) => {
    logger.error.apply(logger, args);
  },
  warn: (...args: any) => {
    logger.warn.apply(logger, args);
  },
  fatal: (...args: any) => {
    logger.fatal.apply(logger, args);
  },
};
