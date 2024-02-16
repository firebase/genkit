import { Options, defineConfig } from 'tsup';
import { defaultOptions } from '../tsup.common.js';

export default defineConfig({
  ...(defaultOptions as Options),
});
