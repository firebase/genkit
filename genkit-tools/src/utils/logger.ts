import * as winston from 'winston';
import * as clc from 'colorette';

export const logger = winston.createLogger({
  level: process.env.DEBUG ? 'debug' : 'info',
  format: winston.format.printf((log) => {
    // Anything logged at 'info' level will show as just the plain message
    if (log.level === 'info') return log.message as string;

    let levelColor: clc.Color;
    switch (log.level) {
      case 'error':
        levelColor = clc.red;
        break;
      case 'warn':
        levelColor = clc.yellow;
        break;
      default:
        // Default is nothing.
        levelColor = (text) => text.toString();
        break;
    }

    const level = log.level.charAt(0).toUpperCase() + log.level.slice(1);
    return `${clc.bold(levelColor(level))}: ${log.message}`;
  }),
  transports: [new winston.transports.Console()],
});
