import * as path from 'path';
import * as fs from 'fs';

interface PackageJson {
  main: string;
}

/**
 * Returns the entry point of a Node.js app.
 * @param directory directory to check
 */
export function getNodeEntryPoint(directory: string): string {
  const packageJsonPath = path.join(directory, 'package.json');
  const defaultMain = 'lib/index.js';
  if (fs.existsSync(packageJsonPath)) {
    const packageJson = JSON.parse(
      fs.readFileSync(packageJsonPath, 'utf8'),
    ) as PackageJson;
    return packageJson.main || defaultMain;
  }
  return defaultMain;
}
