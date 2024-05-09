import { glob } from 'glob';
import * as path from 'path';
import { logger } from '../utils';

async function main() {
  logger.info(`Loading file paths: ${process.argv[2]}`);
  const files = await glob(process.argv[2]);
  for (const file of files) {
    logger.info(`Loading \`${file}\`...`);
    await import(path.join(process.cwd(), file));
  }
}

main();
