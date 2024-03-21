import { readFileSync } from 'fs';
import { join } from 'path';

const packagePath = join(__dirname, '../../package.json');
export const toolsPackage = JSON.parse(readFileSync(packagePath, 'utf8'));
