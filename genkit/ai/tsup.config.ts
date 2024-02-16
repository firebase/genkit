import { Options, defineConfig } from 'tsup';
import { defaultOptions, fromPackageJson } from '../tsup.common.js';
import packageJson from './package.json';

export default defineConfig({
  ...(defaultOptions as Options),
  entry: fromPackageJson(packageJson),
});
