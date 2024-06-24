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

import { InitEvent, record } from '@genkit-ai/tools-common/utils';
import { execSync } from 'child_process';
import extract from 'extract-zip';
import fs from 'fs';
import * as inquirer from 'inquirer';
import ora from 'ora';
import path from 'path';
import {
  InitOptions,
  ModelProvider,
  Platform,
  WriteMode,
  confirm,
  showModelInfo,
} from '../init';

type SampleTarget = 'firebase' | 'googlecloud' | 'nodejs' | 'nextjs';

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

interface PromptOption {
  // Label for prompt option.
  label: string;
  // Plugin name.
  plugin?: string;
}

interface ImportOptions {
  // Spacing around brackets in import
  spacer: ' ' | '';
  // Single or double quotes for import
  quotes: '"' | "'";
}

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

/** Supported platform to plugin name. */
const platformOptions: Record<Platform, PromptOption> = {
  firebase: { label: 'Firebase', plugin: '@genkit-ai/firebase' },
  googlecloud: {
    label: 'Google Cloud',
    plugin: '@genkit-ai/google-cloud',
  },
  other: { label: 'Other platforms', plugin: undefined },
};

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
const sampleTemplatePaths: Record<SampleTarget, string> = {
  firebase: '../../../config/firebase.index.ts.template',
  googlecloud: '../../../config/googleCloud.index.ts.template',
  nodejs: '../../../config/googleCloud.index.ts.template', // This can deviate from GCP template in the future as needed.
  nextjs: '../../../config/nextjs.genkit.ts.template',
};

const nextjsToolsConfigTemplatePath =
  '../../../config/nextjs.genkit-tools.config.js.template';

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

const platformImportOptions: Record<Platform, ImportOptions> = {
  firebase: { spacer: '', quotes: '"' },
  googlecloud: { spacer: ' ', quotes: "'" },
  other: { spacer: ' ', quotes: "'" },
};

/**
 * Initializes a Genkit Node.js project.
 *
 * @param options command-line arguments
 * @param isNew whether the project directory should be newly created
 */
export async function initNodejs(options: InitOptions, isNew: boolean) {
  let { platform, model, distArchive } = options;

  // Validate CLI arguments.
  const supportedPlatforms = Object.keys(platformOptions) as Platform[];
  if (platform && !supportedPlatforms.includes(platform)) {
    throw new Error(
      `\`${platform}\` is not a supported platform for Node.js. Supported platforms: ${supportedPlatforms}`
    );
  }
  const supportedModels = Object.keys(modelOptions) as ModelProvider[];
  if (model && !supportedModels.includes(model)) {
    throw new Error(
      `\`${model}\` is not a supported model provider for Node.js. Supported model providers: ${supportedModels}`
    );
  }

  // Prompt for left-over arguments.
  if (!platform) {
    const answer = await inquirer.prompt<{ platform: Platform }>([
      {
        type: 'list',
        name: 'platform',
        message: 'Select a deployment platform:',
        choices: supportedPlatforms.map((platform) => ({
          name: platformOptions[platform].label,
          value: platform,
        })),
      },
    ]);
    platform = answer.platform;
  }
  var sampleTarget: SampleTarget;
  if (platform === 'other') {
    if (
      isNextJsProject() &&
      (await confirm({
        message:
          'Detected a Next.js project. Would you like to configure Genkit for Next.js?',
        default: true,
      }))
    ) {
      sampleTarget = 'nextjs';
    } else {
      sampleTarget = 'nodejs';
    }
  } else {
    sampleTarget = platform;
  }
  if (!model) {
    const answer = await inquirer.prompt<{ model: ModelProvider }>([
      {
        type: 'list',
        name: 'model',
        message: 'Select a model provider:',
        choices: supportedModels.map((model) => ({
          name: modelOptions[model].label,
          value: model,
        })),
      },
    ]);
    model = answer.model;
  }

  // Compile plugins list.
  const plugins: string[] = [];
  if (platformOptions[platform]?.plugin) {
    plugins.push(platformOptions[platform].plugin!);
  }
  if (modelOptions[model]?.plugin) {
    plugins.push(modelOptions[model].plugin!);
  }

  // Compile NPM packages list.
  const packages = [...externalPackages];
  if (!distArchive) {
    packages.push(...internalPackages);
    packages.push(...plugins);
  }

  // Initialize and configure.
  if (isNew) {
    const spinner = ora('Initializing NPM project').start();
    try {
      execSync('npm init -y', { stdio: 'ignore' });
      spinner.succeed('Successfully initialized NPM project');
    } catch (err) {
      spinner.fail(`Failed to initialize NPM project: ${err}`);
      process.exit(1);
    }
  }
  await installNpmPackages(packages, externalDevPackages, distArchive);
  if (!fs.existsSync('src')) {
    fs.mkdirSync('src');
  }
  await updateTsConfig(options.nonInteractive || isNew);
  await updatePackageJson(options.nonInteractive || isNew);
  if (
    options.nonInteractive ||
    (await confirm({
      message: 'Would you like to generate a sample flow?',
      default: true,
    }))
  ) {
    generateSampleFile(
      platform,
      sampleTarget,
      modelOptions[model].plugin,
      plugins
    );
  }
  generateToolsConfig(sampleTarget);
  showModelInfo(model);

  // Record event.
  await record(new InitEvent(sampleTarget));
}

/**
 * Updates tsconfig.json with required flags for Genkit.
 */
async function updateTsConfig(nonInteractive: boolean) {
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
  const spinner = ora('Updating tsconfig.json').start();
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
      spinner.warn('Skipped updating tsconfig.json');
      return;
  }
  try {
    fs.writeFileSync(tsConfigPath, JSON.stringify(newTsConfig, null, 2));
    spinner.succeed('Successfully updated tsconfig.json');
  } catch (err) {
    spinner.fail(`Failed to update tsconfig.json: ${err}`);
    process.exit(1);
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
  const spinner = ora('Installing NPM packages').start();
  try {
    if (packages.length) {
      execSync(`npm install ${packages.join(' ')} --save`, { stdio: 'ignore' });
    }
    if (devPackages?.length) {
      execSync(`npm install ${devPackages.join(' ')} --save-dev`, {
        stdio: 'ignore',
      });
    }
    if (distArchive) {
      const distDir = 'genkit-dist';
      const outputPath = path.join(process.cwd(), distDir);
      if (!fs.existsSync(distDir)) {
        fs.mkdirSync(distDir);
      }
      await extract(distArchive, { dir: outputPath });
      execSync(`npm install ${outputPath}/*.tgz --save`, { stdio: 'ignore' });
    }
    spinner.succeed('Successfully installed NPM packages');
  } catch (err) {
    spinner.fail(`Failed to install NPM packages: ${err}`);
    process.exit(1);
  }
}

/**
 * Generates a sample index.ts file.
 * @param platform Deployment platform.
 * @param sampleTarget Sample target.
 * @param modelPlugin Model plugin name.
 */
function generateSampleFile(
  platform: Platform,
  sampleTarget: SampleTarget,
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
  const templatePath = path.join(__dirname, sampleTemplatePaths[sampleTarget]);
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
  const spinner = ora('Generating sample file').start();
  try {
    let samplePath = 'src/index.ts';
    if (sampleTarget === 'nextjs') {
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
    fs.writeFileSync(path.join(process.cwd(), samplePath), sample, 'utf8');
    spinner.succeed(`Successfully generated sample file (${samplePath})`);
  } catch (err) {
    spinner.fail(`Failed to generate sample file: ${err}`);
    process.exit(1);
  }
}

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
  const spinner = ora('Updating package.json').start();
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
      spinner.warn('Skipped updating package.json');
      return;
  }
  try {
    fs.writeFileSync(packageJsonPath, JSON.stringify(newPackageJson, null, 2));
    spinner.succeed('Successfully updated package.json');
  } catch (err) {
    spinner.fail(`Failed to update package.json: ${err}`);
    process.exit(1);
  }
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
 * Generates an appropriate tools config for the given platform.
 * @param platform platform
 */
function generateToolsConfig(sampleTarget: SampleTarget) {
  if (sampleTarget === 'nextjs') {
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
    const spinner = ora('Updating genkit-tools.conf.js').start();
    try {
      fs.writeFileSync(
        path.join(process.cwd(), 'genkit-tools.conf.js'),
        template,
        'utf8'
      );
      spinner.succeed('Successfully updated genkit-tools.conf.js');
    } catch (err) {
      spinner.fail(`Failed to update genkit-tools.conf.js: ${err}`);
      process.exit(1);
    }
  }
}

/**
 * Detects whether the project directory is a Next.js app.
 */
function isNextJsProject(projectDir: string = process.cwd()): boolean {
  const hasNextConfig = fs.existsSync(path.join(projectDir, 'next.config.js'));
  let packageJson;
  try {
    packageJson = JSON.parse(
      fs.readFileSync(path.join(projectDir, 'package.json'), 'utf8')
    );
  } catch (error) {
    return false;
  }
  const hasNextDependency =
    packageJson.dependencies && packageJson.dependencies.next;
  return hasNextConfig || hasNextDependency;
}

/**
 * Prompts for what type of write to perform when there is a conflict.
 */
export async function promptWriteMode(
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
