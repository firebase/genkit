export const defaultOptions = {
  format: ['cjs', 'esm'],
  dts: true,
  sourcemap: true,
  clean: true,
  shims: true,
  outDir: 'lib',
  entry: ['src/**/*.ts'],
  bundle: false,
  treeshake: false,
};

/**
 *
 */
export function fromPackageJson(packageJson: {
  exports?: { [key: string]: { import: string } };
}): string[] {
  if (!packageJson.exports) return ['./src/index.ts'];
  const out: string[] = [];
  for (const key in packageJson.exports) {
    if (Object.prototype.hasOwnProperty.call(packageJson.exports, key)) {
      const importFile = packageJson.exports[key].import;
      out.push(importFile.replace('./lib', './src').replace('.mjs', '.ts'));
    }
  }
  return out;
}
