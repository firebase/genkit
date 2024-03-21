import Configstore from 'configstore';
import { toolsPackage } from './package';

export const configstore = new Configstore(toolsPackage.name);
