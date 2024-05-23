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

import { Runtime } from '@genkit-ai/tools-common/runner';
import {
  InitEvent,
  detectRuntime,
  logger,
  record,
} from '@genkit-ai/tools-common/utils';
import { execSync } from 'child_process';
import { Command } from 'commander';
import extract from 'extract-zip';
import * as fs from 'fs';
import * as inquirer from 'inquirer';
import * as path from 'path';

type Platform = 'firebase' | 'googlecloud' | 'nodejs' | 'nextjs';
type ModelProvider = 'googleai' | 'vertexai' | 'ollama' | 'none';
type WriteMode = 'keep' | 'overwrite' | 'merge';

interface PromptOption {
  // Label for prompt option.
  label: string;
  // Plugin name.
  plugin?: string;
}

interface PluginInfo {
  // Imported items from `name` (can be comma list).
  imports: string;
  // Initializer call.
  init: string;
  // Model name as an imported reference.
  model?: string;
  // Model name as a string reference.
  modelStr?: string;
}

interface InitOptions {
  // Deployment platform.
  platform: Platform;
  // Model provider.
  model: ModelProvider;
  // Path to local Genkit dist archive.
  distArchive: string;
  // Non-interactive mode.
  nonInteractive: boolean;
}

interface ImportOptions {
  // Spacing around brackets in import
  spacer: ' ' | '';
  // Single or double quotes for import
  quotes: '"' | "'";
}

/** Supported platform to plugin name. */
const platformOptions: Record<Platform, PromptOption> = {
  firebase: { label: 'Firebase', plugin: '@genkit-ai/firebase' },
  googlecloud: {
    label: 'Google Cloud',
    plugin: '@genkit-ai/google-cloud',
  },
  nodejs: { label: 'Node.js', plugin: undefined },
  nextjs: {
    label: 'Next.js (Experimental)',
    plugin: undefined,
  },
};

/** Model to plugin name. */
const modelOptions: Record<ModelProvider, PromptOption> = {
  googleai: { label: 'Google AI', plugin: '@genkit-ai/googleai' },
  vertexai: {
    label: 'Google Cloud Vertex AI',
    plugin: '@genkit-ai/vertexai',
  },
  ollama: { label: 'Ollama (e.g. Gemma)', plugin: 'genkitx-ollama' },
  none: { label: 'None', plugin: undefined },
};

const platformImportOptions: Record<Platform, ImportOptions> = {
  firebase: { spacer: '', quotes: '"' },
  googlecloud: { spacer: ' ', quotes: "'" },
  nodejs: { spacer: ' ', quotes: "'" },
  nextjs: { spacer: ' ', quotes: "'" },
};

/** External packages required to use Genkit. */
const externalPackages = ['zod', 'express'];

/** External dev packages required to use Genkit. */
const externalDevPackages = ['typescript'];

/** Internal packages required to use Genkit. */
const internalPackages = [
  '@genkit-ai/core',
  '@genkit-ai/ai',
  '@genkit-ai/dotprompt',
  '@genkit-ai/flow',
];

/** Plugin name to descriptor. */
const pluginToInfo: Record<string, PluginInfo> = {
  '@genkit-ai/firebase': {
    imports: 'firebase',
    init: 'firebase()',
  },
  '@genkit-ai/google-cloud': {
    imports: 'googleCloud',
    init: 'googleCloud()',
  },
  '@genkit-ai/vertexai': {
    imports: 'vertexAI',
    init: "vertexAI({ location: 'us-central1' })",
    model: 'geminiPro',
  },
  'genkitx-ollama': {
    imports: 'ollama',
    init: `ollama({
      models: [{ name: 'gemma' }],
      serverAddress: 'http://127.0.0.1:11434', // default ollama local address
    })`,
    modelStr: "'ollama/gemma'",
  },
  '@genkit-ai/googleai': {
    imports: 'googleAI',
    init: 'googleAI()',
    model: 'geminiPro',
  },
};

/** Platform to sample flow template paths. */
const sampleTemplatePaths: Record<Platform, string> = {
  firebase: '../../config/firebase.index.ts.template',
  googlecloud: '../../config/googleCloud.index.ts.template',
  nodejs: '../../config/googleCloud.index.ts.template', // This can deviate from GCP template in the future as needed.
  nextjs: '../../config/nextjs.genkit.ts.template',
};

const nextjsToolsConfigTemplatePath =
  '../../config/nextjs.genkit-tools.config.js.template';

/** Supported runtimes for the init command. */
const supportedRuntimes: Runtime[] = ['node'];

export const init = new Command('init')
  .description('initialize a project directory with Genkit')
  .option(
    '-p, --platform <platform>',
    'Deployment platform (firebase, googlecloud, or nodejs)'
  )
  .option(
    '-m, --model <model>',
    'Model provider (googleai, vertexai, ollama, or none)'
  )
  .option(
    '--non-interactive',
    'Run init in non-interactive mode (experimental)'
  )
  .option(
    '-d, --dist-archive <distArchive>',
    'Path to local Genkit dist archive'
  )
  .action(async (options: InitOptions) => {
    let { platform, model, distArchive } = options;
    const supportedPlatforms = Object.keys(platformOptions) as Platform[];
    if (platform && !supportedPlatforms.includes(platform)) {
      logger.error(
        `\`${platform}\` is not a supported platform. Supported platforms: ${supportedPlatforms}`
      );
      process.exit(1);
    }
    const supportedModels = Object.keys(modelOptions) as ModelProvider[];
    if (model && !supportedModels.includes(model)) {
      logger.error(
        `\`${model}\` is not a supported model provider. Supported model providers: ${supportedModels}`
      );
      process.exit(1);
    }
    const runtime = detectRuntime(process.cwd());
    if (!runtime) {
      logger.info('No runtime was detected in the current directory.');
      if (
        await confirm({
          default: true,
          message: 'Would you like to initialize a Node.js Genkit project?',
        })
      ) {
        execSync(`npm init -y`, { stdio: 'inherit' });
      } else {
        logger.error(
          'Please re-run `genkit init` from an active project directory.'
        );
        process.exit(1);
      }
    } else if (!supportedRuntimes.includes(runtime)) {
      logger.error(
        `The runtime could not be detected or is not supported. Supported runtimes: ${supportedRuntimes}`
      );
      process.exit(1);
    }
    if (!platform) {
      const answer = await inquirer.prompt<{ platform: Platform }>([
        {
          type: 'list',
          name: 'platform',
          message: 'Select the deployment platform:',
          choices: supportedPlatforms.map((platform) => ({
            name: platformOptions[platform].label,
            value: platform,
          })),
        },
      ]);
      platform = answer.platform;
    }
    const plugins: string[] = [];
    if (platformOptions[platform]?.plugin) {
      plugins.push(platformOptions[platform].plugin!);
    }
    if (!model) {
      const answer = await inquirer.prompt<{ model: ModelProvider }>([
        {
          type: 'list',
          name: 'model',
          message: 'Select the model provider:',
          choices: supportedModels.map((model) => ({
            name: modelOptions[model].label,
            value: model,
          })),
        },
      ]);
      model = answer.model;
    }
    if (model === 'googleai') {
      logger.warn(
        `${modelOptions['googleai'].label} is currently available in limited regions. For a complete list, see https://ai.google.dev/available_regions#available_regions`
      );
    }
    if (modelOptions[model]?.plugin) {
      plugins.push(modelOptions[model].plugin!);
    }
    const packages = [...externalPackages];
    if (!distArchive) {
      packages.push(...internalPackages);
      packages.push(...plugins);
    }
    try {
      await installNpmPackages(packages, externalDevPackages, distArchive);
      if (!fs.existsSync('src')) {
        fs.mkdirSync('src');
      }
      await updateTsConfig(options.nonInteractive);
      await updatePackageJson(options.nonInteractive);
      if (
        options.nonInteractive ||
        (await confirm({
          message: 'Would you like to generate a sample flow?',
          default: true,
        }))
      ) {
        generateSampleFile(platform, modelOptions[model].plugin, plugins);
      }
      generateToolsConfig(platform);
    } catch (error) {
      logger.error(error);
      process.exit(1);
    }
    if (model === 'vertexai') {
      logger.info(
        `Run the following command to enable Vertex AI in your Google Cloud project:\n\n  gcloud services enable aiplatform.googleapis.com\n`
      );
    }
    if (model === 'ollama') {
      logger.info(
        `If you don't have Ollama already installed and configured, refer to https://developers.google.com/genkit/plugins/ollama\n`
      );
    }
    await record(new InitEvent(platform));
    logger.info('Genkit successfully initialized.');
  });

/**
 * Updates package.json with Genkit-expected fields.
 */
async function updatePackageJson(nonInteractive: boolean) {
  const packageJsonPath = path.join(process.cwd(), 'package.json');
  // package.json should exist before reaching this point.
  if (!fs.existsSync(packageJsonPath)) {
    throw new Error('Failed to find package.json.');
  }
  const existingPackageJson = JSON.parse(
    fs.readFileSync(packageJsonPath, 'utf8')
  );
  const choice = nonInteractive
    ? 'overwrite'
    : await promptWriteMode(
        'Would you like to update your package.json with suggested settings?'
      );
  const packageJson = {
    main: 'lib/index.js',
    scripts: {
      start: 'node lib/index.js',
      build: 'tsc',
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
        // Main will always be overwritten to match tsconfig.
        main: packageJson.main,
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
 * Generates an appropriate tools config for the given platform.
 * @param platform platform
 */
function generateToolsConfig(platform: Platform) {
  if (platform === 'nextjs') {
    const templatePath = path.join(__dirname, nextjsToolsConfigTemplatePath);
    let template = fs.readFileSync(templatePath, 'utf8');
    if (fs.existsSync('src/app')) {
      template = template.replace('$GENKIT_HARNESS_FILES', `'./src/app/*.ts'`);
    } else if (fs.existsSync('app')) {
      template = template.replace('$GENKIT_HARNESS_FILES', `'./app/*.ts'`);
    } else {
      throw new Error(
        'Unable to resolve source folder (app or src/app) of you next.js app.'
      );
    }
    const configPath = path.join(process.cwd(), 'genkit-tools.conf.js');
    fs.writeFileSync(configPath, template, 'utf8');
  }
}

/**
 * Generates a sample index.ts file.
 * @param platform Deployment platform.
 * @param modelPlugin Model plugin name.
 */
function generateSampleFile(
  platform: Platform,
  modelPlugin: string | undefined,
  configPlugins: string[]
) {
  const modelImport =
    modelPlugin && pluginToInfo[modelPlugin].model
      ? generateImportStatement(
          pluginToInfo[modelPlugin].model!,
          modelPlugin,
          platformImportOptions[platform]
        )
      : '';
  const templatePath = path.join(__dirname, sampleTemplatePaths[platform]);
  let template = fs.readFileSync(templatePath, 'utf8');
  const sample = renderConfig(
    configPlugins,
    platform,
    template
      .replace('$GENKIT_MODEL_IMPORT', modelImport)
      .replace(
        '$GENKIT_MODEL',
        modelPlugin
          ? pluginToInfo[modelPlugin].model ||
              pluginToInfo[modelPlugin].modelStr ||
              ''
          : "'' /* TODO: Set a model. */"
      )
  );
  logger.info('Generating sample file...');
  let samplePath = 'src/index.ts';
  if (platform === 'nextjs') {
    if (fs.existsSync('src/app')) {
      samplePath = 'src/app/genkit.ts';
    } else if (fs.existsSync('app')) {
      samplePath = 'app/genkit.ts';
    } else {
      throw new Error(
        'Unable to resolve source folder (app or src/app) of you next.js app.'
      );
    }
  }
  fs.writeFileSync(samplePath, sample, 'utf8');
}

function renderConfig(
  pluginNames: string[],
  platform: Platform,
  template: string
): string {
  const imports = pluginNames
    .map((pluginName) =>
      generateImportStatement(
        pluginToInfo[pluginName].imports,
        pluginName,
        platformImportOptions[platform]
      )
    )
    .join('\n');
  const plugins =
    pluginNames
      .map((pluginName) => `    ${pluginToInfo[pluginName].init},`)
      .join('\n') || '    /* Add your plugins here. */';
  return template
    .replace('$GENKIT_CONFIG_IMPORTS', imports)
    .replace('$GENKIT_CONFIG_PLUGINS', plugins);
}

function generateImportStatement(
  imports: string,
  name: string,
  opts: ImportOptions
): string {
  return `import {${opts.spacer}${imports}${opts.spacer}} from ${opts.quotes}${name}${opts.quotes};`;
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
async function updateTsConfig(nonInteractive: boolean) {
  try {
    const tsConfigPath = path.join(process.cwd(), 'tsconfig.json');
    let existingTsConfig = undefined;
    if (fs.existsSync(tsConfigPath)) {
      existingTsConfig = JSON.parse(fs.readFileSync(tsConfigPath, 'utf-8'));
    }
    let choice: WriteMode = 'overwrite';
    if (!nonInteractive && existingTsConfig) {
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
