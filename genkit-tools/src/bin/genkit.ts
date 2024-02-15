#!/usr/bin/env node

/** Shim wrapper for genkit CLI */

import { startCLI } from '../cli';

void (async () => {
  await startCLI();
  process.exit();
})();
