import { Options, defineConfig } from 'tsup';
import { defaultOptions } from '../../tsup.common';

export default defineConfig({
  ...(defaultOptions as Options),
});
