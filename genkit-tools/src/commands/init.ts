/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { execSync } from 'child_process';
import { Command } from 'commander';
import extract from 'extract-zip';
import * as fs from 'fs';
import * as inquirer from 'inquirer';
import * as path from 'path';
import { InitEvent, record } from '../utils/analytics';
import { logger } from '../utils/logger';

/** Maps from supported platforms to required plugins. */
const platformToPlugins: Record<Platform, string[]> = {
  firebase: ['@genkit-ai/plugin-firebase'],
  gcp: ['@genkit-ai/plugin-gcp'],
  other: [],
};
/** Maps from model name to plugin. */
const modelToPlugin: Record<string, string> = {
  'Google AI': '@genkit-ai/plugin-google-genai',
  'Vertex AI': '@genkit-ai/plugin-vertex-ai',
  OpenAI: '@genkit-ai/plugin-openai',
};
/** External packages required to use Genkit. */
const externalPackages = ['zod', 'express'];
/** Core packages required to use Genkit. */
const corePackages = [
  '@genkit-ai/common',
  '@genkit-ai/ai',
  '@genkit-ai/dotprompt',
  '@genkit-ai/flow',
];
/** Core dev packages required to use Genkit. */
const coreDevPackages = ['typescript'];
/** Plugin name to template insertion info. */
const pluginToInfo: Record<string, PluginInfo> = {
  '@genkit-ai/plugin-firebase': {
    name: '@genkit-ai/plugin-firebase',
    import: 'firebase',
    init: 'firebase({})',
  },
  '@genkit-ai/plugin-gcp': {
    name: '@genkit-ai/plugin-gcp',
    import: 'gcp',
    init: 'gcp({})',
  },
  '@genkit-ai/plugin-vertex-ai': {
    name: '@genkit-ai/plugin-vertex-ai',
    import: 'vertexAI',
    init: "vertexAI({ location: 'us-central1' })",
    model: 'geminiPro',
  },
  '@genkit-ai/plugin-openai': {
    name: '@genkit-ai/plugin-openai',
    import: 'openAI',
    init: 'openAI()',
    model: 'gpt35Turbo',
  },
  '@genkit-ai/plugin-google-genai': {
    name: '@genkit-ai/plugin-google-genai',
    import: 'googleAI',
    init: 'googleAI()',
    model: 'geminiPro',
  },
};
const configTemplatePath = '../../config/genkit.conf.ts.template';
const sampleTemplatePaths: Record<Platform, string> = {
  firebase: '../../config/firebase.index.ts.template',
  gcp: '../../config/gcp.index.ts.template',
  other: '../../config/gcp.index.ts.template', // This can deviate from GCP template in the future as needed.
};
/** Supported runtimes for the init command. */
const supportedRuntimes: Runtime[] = ['node'];

type Platform = 'firebase' | 'gcp' | 'other';
type Runtime = 'node' | undefined;
type WriteMode = 'keep' | 'overwrite' | 'merge';

interface PluginInfo {
  name: string;
  import: string;
  init: string;
  model?: string;
}

interface InitOptions {
  platform: Platform;
  distArchive: string;
}

export const init = new Command('init')
  .description('Initialize a project for Genkit')
  .option(
    '-p, --platform <platform>',
    'Deployment platform (firebase, gcp, or other)'
  )
  .option(
    '-d, --dist-archive <distArchive>',
    'Path to local Genkit dist archive'
  )
  .action(async (options: InitOptions) => {
    let { platform, distArchive } = options;
    const supportedPlatforms = Object.keys(platformToPlugins);
    if (supportedPlatforms.includes(platform)) {
      logger.error(
        `\`${platform}\` is not a supported platform. Supported platforms: ${supportedPlatforms}`
      );
      process.exit(1);
    }
    const runtime = detectRuntime();
    if (!supportedRuntimes.includes(runtime)) {
      logger.error(
        `The runtime could not be detected or is not supported. Supported runtimes: ${supportedRuntimes}`
      );
      process.exit(1);
    }
    if (!platform) {
      const answer = await inquirer.prompt([
        {
          type: 'list',
          name: 'platform',
          message: 'Select the deployment platform:',
          choices: supportedPlatforms,
        },
      ]);
      platform = answer.platform;
    }
    const plugins = [...(platformToPlugins[platform] || [])];
    const { model } = await inquirer.prompt([
      {
        type: 'list',
        name: 'model',
        message: 'Select the model:',
        choices: Object.keys(modelToPlugin),
      },
    ]);
    plugins.push(modelToPlugin[model]);
    const packages = [...externalPackages];
    if (!distArchive) {
      packages.push(...corePackages);
      packages.push(...plugins);
    }
    try {
      await installNpmPackages(packages, coreDevPackages, distArchive);
      if (!fs.existsSync('src')) {
        fs.mkdirSync('src');
      }
      generateConfigFile(plugins, platform);
      await updateTsConfig();
      await updatePackageJson();
      if (
        await confirm({
          message: 'Would you like to generate a sample flow?',
          default: true,
        })
      ) {
        generateSampleFile(platform, modelToPlugin[model]);
      }
    } catch (error) {
      logger.error(error);
      process.exit(1);
    }
    if (model === 'Vertex AI') {
      logger.info(
        `Run the following command to enable Vertex AI in your Google Cloud project:\n\n  gcloud services enable aiplatform.googleapis.com\n`
      );
    }
    await record(new InitEvent(platform));
    logger.info('Genkit successfully initialized.');
  });

/**
 * Updates package.json with Genkit-expected fields.
 */
async function updatePackageJson() {
  const packageJsonPath = path.join(process.cwd(), 'package.json');
  // package.json should exist before reaching this point.
  if (!fs.existsSync(packageJsonPath)) {
    throw new Error('Failed to find package.json.');
  }
  const existingPackageJson = JSON.parse(
    fs.readFileSync(packageJsonPath, 'utf8')
  );
  const choice = await promptWriteMode(
    'Would you like to update your package.json with suggested settings?'
  );
  const packageJson = {
    main: 'lib/index.js',
    scripts: {
      start: 'node lib/index.js',
      compile: 'tsc',
      build: 'npm run build:clean && npm run compile',
      'build:clean': 'rm -rf ./lib',
      'build:watch': 'tsc --watch',
    },
  };
  let newPackageJson = {};
  switch (choice) {
    case 'overwrite':
      newPackageJson = {
        ...existingPackageJson,
        ...packageJson,
        scripts: {
          ...existingPackageJson.scripts,
          ...packageJson.scripts,
        },
      };
      break;
    case 'merge':
      newPackageJson = {
        ...packageJson,
        ...existingPackageJson,
        scripts: {
          ...packageJson.scripts,
          ...existingPackageJson.scripts,
        },
      };
      break;
    case 'keep':
      logger.info('Leaving package.json unchanged.');
      return;
  }
  logger.info('Updating package.json...');
  fs.writeFileSync(packageJsonPath, JSON.stringify(newPackageJson, null, 2));
}

/**
 * Generates a sample index.ts file.
 * @param platform Deployment platform.
 */
function generateSampleFile(platform: Platform, modelPlugin: string) {
  const modelImport = `import { ${pluginToInfo[modelPlugin].model} } from '${modelPlugin}';`;
  const templatePath = path.join(__dirname, sampleTemplatePaths[platform]);
  let template = fs.readFileSync(templatePath, 'utf8');
  const sample = template
    .replace('$GENKIT_MODEL_IMPORT', modelImport)
    .replace('$GENKIT_MODEL', pluginToInfo[modelPlugin].model || '');
  logger.info('Generating sample file...');
  fs.writeFileSync('src/index.ts', sample, 'utf8');
}

/**
 * Generates a genkit.conf file.
 * @param pluginInfos List of plugin infos.
 * @param platform Deployment platform.
 */
function generateConfigFile(pluginNames: string[], platform?: Platform): void {
  const imports = pluginNames
    .map(
      (pluginName) =>
        `import { ${pluginToInfo[pluginName].import} } from '${pluginName}';`
    )
    .join('\n');
  const plugins = pluginNames
    .map((pluginName) => `    ${pluginToInfo[pluginName].init},`)
    .join('\n');
  const storePlugin =
    platform === 'firebase' || platform === 'gcp' ? 'firebase' : undefined;
  const store = storePlugin
    ? `\n  flowStateStore: '${storePlugin}',\n  traceStore: '${storePlugin}',`
    : '';
  try {
    const templatePath = path.join(__dirname, configTemplatePath);
    const template = fs.readFileSync(templatePath, 'utf8');
    const config = template
      .replace('$GENKIT_IMPORTS', imports)
      .replace('$GENKIT_PLUGINS', plugins)
      .replace('$GENKIT_STORE', store);
    const outputPath = path.join(process.cwd(), 'src/genkit.conf.ts');
    logger.info('Generating genkit.conf.ts...');
    fs.writeFileSync(outputPath, config, 'utf8');
  } catch (error) {
    throw new Error(`Failed to generate genkit.conf file: ${error}`);
  }
}

/**
 * Prompts for what type of write to perform when there is a conflict.
 */
async function promptWriteMode(
  message: string,
  defaultOption: WriteMode = 'merge'
): Promise<WriteMode> {
  const answers = await inquirer.prompt([
    {
      type: 'list',
      name: 'option',
      message,
      choices: [
        { name: 'Set if unset', value: 'merge' },
        { name: 'Overwrite', value: 'overwrite' },
        { name: 'Keep unchanged', value: 'keep' },
      ],
      default: defaultOption,
    },
  ]);
  return answers.option;
}

/**
 * Updates tsconfig.json with required flags for Genkit.
 */
async function updateTsConfig() {
  try {
    const tsConfigPath = path.join(process.cwd(), 'tsconfig.json');
    let existingTsConfig = undefined;
    if (fs.existsSync(tsConfigPath)) {
      existingTsConfig = JSON.parse(fs.readFileSync(tsConfigPath, 'utf-8'));
    }
    let choice: WriteMode = 'overwrite';
    if (existingTsConfig) {
      choice = await promptWriteMode(
        'Would you like to update your tsconfig.json with suggested settings?'
      );
    }
    const tsConfig = {
      compileOnSave: true,
      include: ['src'],
      compilerOptions: {
        module: 'commonjs',
        noImplicitReturns: true,
        outDir: 'lib',
        sourceMap: true,
        strict: true,
        target: 'es2017',
        skipLibCheck: true,
        esModuleInterop: true,
      },
    };
    let newTsConfig = {};
    switch (choice) {
      case 'overwrite':
        newTsConfig = {
          ...existingTsConfig,
          ...tsConfig,
          compilerOptions: {
            ...existingTsConfig?.compilerOptions,
            ...tsConfig.compilerOptions,
          },
        };
        break;
      case 'merge':
        newTsConfig = {
          ...tsConfig,
          ...existingTsConfig,
          compilerOptions: {
            ...tsConfig.compilerOptions,
            ...existingTsConfig?.compilerOptions,
          },
        };
        break;
      case 'keep':
        logger.info('Leaving tsconfig.json unchanged.');
        return;
    }
    logger.info('Updating tsconfig.json...');
    fs.writeFileSync(tsConfigPath, JSON.stringify(newTsConfig, null, 2));
  } catch (error) {
    throw new Error(`Failed to update tsconfig.json: ${error}`);
  }
}

/**
 * Installs and saves NPM packages to package.json.
 * @param packages List of NPM packages to install.
 * @param devPackages List of NPM dev packages to install.
 */
async function installNpmPackages(
  packages: string[],
  devPackages?: string[],
  distArchive?: string
): Promise<void> {
  try {
    logger.info('Installing packages...');
    if (packages.length) {
      execSync(`npm install ${packages.join(' ')} --save`, {
        stdio: 'inherit',
      });
    }
    if (devPackages?.length) {
      execSync(`npm install ${devPackages.join(' ')} --save-dev`, {
        stdio: 'inherit',
      });
    }
    if (distArchive) {
      const distDir = 'genkit-dist';
      const outputPath = path.join(process.cwd(), distDir);
      if (!fs.existsSync(distDir)) {
        fs.mkdirSync(distDir);
      }
      await extract(distArchive, { dir: outputPath });
      execSync(`npm install ${outputPath}/*.tgz --save`);
    }
  } catch (error) {
    throw new Error(`Failed to install NPM packages: ${error}`);
  }
}

/**
 * Detects what runtime is used in the current directory.
 * @returns Runtime of the project directory.
 */
function detectRuntime(): Runtime {
  if (fs.existsSync(path.join(process.cwd(), 'package.json'))) {
    return 'node';
  }
  return undefined;
}

async function confirm(args: {
  default?: boolean;
  message?: string;
}): Promise<boolean> {
  const message = args.message ?? `Do you wish to continue?`;
  const answer = await inquirer.prompt({
    type: 'confirm',
    name: 'confirm',
    message,
    default: args.default,
  });
  return answer.confirm;
}
