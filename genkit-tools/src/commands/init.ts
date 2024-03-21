import { execSync } from 'child_process';
import { Command } from 'commander';
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
/** Core packages required to use Genkit. */
const corePackages = [
  '@genkit-ai/common',
  '@genkit-ai/ai',
  '@genkit-ai/dotprompt',
  '@genkit-ai/flow',
  'zod',
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
  other: '',
};
/** Supported runtimes for the init command. */
const supportedRuntimes: Runtime[] = ['node'];

type Platform = 'firebase' | 'gcp' | 'other';
type Runtime = 'node' | undefined;

interface PluginInfo {
  name: string;
  import: string;
  init: string;
  model?: string;
}

interface InitOptions {
  platform: Platform;
}

interface TsConfig {
  compilerOptions?: {
    esModuleInterop?: boolean;
    skipLibCheck?: boolean;
    noUnusedLocals?: boolean;
  };
}

export const init = new Command('init')
  .description('Initialize a project for Genkit')
  .option(
    '-p, --platform <platform>',
    'Deployment platform (firebase, gcp, or other)'
  )
  .action(async (options: InitOptions) => {
    let { platform } = options;
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
    let generateSample = false;
    if (model !== 'Vertex AI' && platform !== 'other') {
      generateSample = await confirm({
        message: 'Would you like to generate a sample flow?',
        default: true,
      });
    }
    const packages = [...corePackages, ...plugins];
    const storePlugin =
      platform === 'firebase' || platform === 'gcp' ? 'firebase' : undefined;
    try {
      logger.info('Installing Genkit plugins...');
      installNpmPackages(packages, coreDevPackages);
      logger.info('Generating genkit.conf...');
      generateConfigFile(plugins, storePlugin);
      logger.info('Updating tsconfig.json...');
      updateTsConfig();
      if (generateSample) {
        logger.info('Generating sample file...');
        generateSampleFile(platform, modelToPlugin[model]);
      }
    } catch (error) {
      logger.error(error);
      process.exit(1);
    }

    await record(new InitEvent(platform));
    logger.info('Genkit successfully initialized.');
  });

/**
 * Generates a sample index.ts file.
 * @param platform Deployment platform.
 */
function generateSampleFile(platform: Platform, modelPlugin: string) {
  const templatePath = path.join(__dirname, sampleTemplatePaths[platform]);
  let template = fs.readFileSync(templatePath, 'utf8');
  const modelImport = `import { ${pluginToInfo[modelPlugin].model} } from '${modelPlugin}';`;
  template = template
    .replace('$GENKIT_MODEL_IMPORT', modelImport)
    .replace('$GENKIT_MODEL', pluginToInfo[modelPlugin].model || '');
  const outputPath = 'src/index.ts';
  fs.writeFileSync(outputPath, template, 'utf8');
}

/**
 * Generates a genkit.conf file.
 * @param pluginInfos List of plugin infos.
 * @param storePlugin Name of plugin to use for stores.
 */
function generateConfigFile(
  pluginNames: string[],
  storePlugin: string | undefined
): void {
  const templatePath = path.join(__dirname, configTemplatePath);
  // TODO: Allow user input for config file path.
  const outputPath = path.join(process.cwd(), 'src/genkit.conf.ts');
  const imports = pluginNames
    .map(
      (pluginName) =>
        `import { ${pluginToInfo[pluginName].import} } from '${pluginName}';`
    )
    .join('\n');
  const plugins = pluginNames
    .map((pluginName) => `    ${pluginToInfo[pluginName].init},`)
    .join('\n');
  const store = storePlugin
    ? `\n  flowStateStore: '${storePlugin}',\n  traceStore: '${storePlugin}',`
    : '';
  try {
    const template = fs.readFileSync(templatePath, 'utf8');
    const config = template
      .replace('$GENKIT_IMPORTS', imports)
      .replace('$GENKIT_PLUGINS', plugins)
      .replace('$GENKIT_STORE', store);
    fs.writeFileSync(outputPath, config, 'utf8');
  } catch (error) {
    throw new Error(`Failed to generate genkit.conf file: ${error}`);
  }
}

/**
 * Updates tsconfig.json with required flags for Genkit.
 */
function updateTsConfig() {
  try {
    const tsConfigPath = path.join(process.cwd(), 'tsconfig.json');
    let tsConfig: TsConfig = {};
    if (fs.existsSync(tsConfigPath)) {
      const tsConfigContent = fs.readFileSync(tsConfigPath, 'utf-8');
      tsConfig = JSON.parse(tsConfigContent) as TsConfig;
    }
    tsConfig.compilerOptions = {
      ...tsConfig.compilerOptions,
      esModuleInterop: true,
      skipLibCheck: true,
    };
    fs.writeFileSync(tsConfigPath, JSON.stringify(tsConfig, null, 2));
  } catch (error) {
    throw new Error(`Failed to update tsconfig.json: ${error}`);
  }
}

/**
 * Installs and saves NPM packages to package.json.
 * @param packages List of NPM packages to install.
 * @param devPackages List of NPM dev packages to install.
 */
function installNpmPackages(
  packages: string[],
  devPackages: string[] | undefined
): void {
  try {
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
