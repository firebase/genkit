import Configstore from 'configstore';
import { readFileSync } from 'fs';
import { join } from 'path';

const packagePath = join(__dirname, '../../package.json');
const packageJson = JSON.parse(readFileSync(packagePath, 'utf8'));

export const configstore = new Configstore(packageJson.name);
