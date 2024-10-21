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

import { InitEvent, logger, record } from '@genkit-ai/tools-common/utils';
import { execSync } from 'child_process';
import fs from 'fs';
import * as inquirer from 'inquirer';
import ora from 'ora';
import path from 'path';
import { InitOptions, ModelProvider, confirm, showModelInfo } from '../init';

interface ModelOption {
  // Label for prompt option.
  label: string;
  // Package name.
  package: string;
  // Init call.
  init: string;
  // Model lookup call.
  lookup: string;
}

/** Path to Genkit sample template. */
const templatePath = '../../../config/main.go.template';

/** Model to plugin name. */
const modelOptions: Record<ModelProvider, ModelOption> = {
  googleai: {
    label: 'Google AI',
    package: 'github.com/firebase/genkit/go/plugins/googleai',
    init: `// Initialize the Google AI plugin. When you pass an empty string for the
\t// apiKey parameter, the Google AI plugin will use the value from the
\t// GOOGLE_GENAI_API_KEY environment variable, which is the recommended
\t// practice.
\tif err := googleai.Init(ctx, nil); err != nil {
\t\tlog.Fatal(err)
\t}`,
    lookup: `// The Google AI API provides access to several generative models. Here,
\t\t// we specify gemini-1.5-flash.
\t\tm := googleai.Model("gemini-1.5-flash")`,
  },
  vertexai: {
    label: 'Google Cloud Vertex AI',
    package: 'github.com/firebase/genkit/go/plugins/vertexai',
    init: `// Initialize the Vertex AI plugin. When you pass an empty string for the
\t// projectID parameter, the Vertex AI plugin will use the value from the
\t// GCLOUD_PROJECT environment variable. When you pass an empty string for
\t// the location parameter, the plugin uses the default value, us-central1.
\tif err := vertexai.Init(ctx, nil); err != nil {
\t\tlog.Fatal(err)
\t}`,
    lookup: `// The Vertex AI API provides access to several generative models. Here,
\t\t// we specify gemini-1.5-flash.
\t\tm := vertexai.Model("gemini-1.5-flash")`,
  },
  ollama: {
    label: 'Ollama (e.g. Gemma)',
    package: 'github.com/firebase/genkit/go/plugins/ollama',
    init: `// Initialize the Ollama plugin.
\terr := ollama.Init(ctx,
\t\t// The address of your Ollama API server. This is often a different host
\t\t// from your app backend (which runs Genkit), in order to run Ollama on
\t\t// a GPU-accelerated machine.
\t\t"http://127.0.0.1:11434")
\tif err != nil {
\t\tlog.Fatal(err)
\t}
\t// The models you want to use. These must already be downloaded and
\t// available to the Ollama server.
\tollama.DefineModel(ollama.ModelDefinition{Name: "gemma"}, nil)`,
    lookup: `// Ollama provides an interface to many open generative models. Here,
\t\t// we specify Google's Gemma model, which we configured the Ollama
\t\t// plugin to provide, above.
\t\tm := ollama.Model("gemma")`,
  },
  none: {
    label: 'None',
    package: '',
    init: 'nil // TODO: Initialize a model.',
    lookup: 'nil // TODO: Look up a model.',
  },
};

/** Supported platform to plugin name. */
const platformOptions: Record<string, string> = {
  googlecloud: 'Google Cloud',
  other: 'Other platforms',
};

/** Packages required to use Genkit. */
const corePackages = [
  'github.com/firebase/genkit/go/ai',
  'github.com/firebase/genkit/go/genkit',
];

/**
 * Initializes a Genkit Go project.
 *
 * @param options command-line arguments
 * @param isNew whether the project directory should be newly created
 */
export async function initGo(options: InitOptions, isNew: boolean) {
  let { platform, model } = options;

  // Validate CLI arguments.
  const supportedPlatforms = Object.keys(platformOptions);
  if (platform && !supportedPlatforms.includes(platform)) {
    throw new Error(
      `\`${platform}\` is not a supported platform for Go. Supported platforms: ${supportedPlatforms}`
    );
  }
  const supportedModels = Object.keys(modelOptions) as ModelProvider[];
  if (model && !supportedModels.includes(model)) {
    throw new Error(
      `\`${model}\` is not a supported model provider for Go. Supported model providers: ${supportedModels}`
    );
  }

  // Prompt for left-over arguments.
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

  // Compile Go packages list.
  const packages = [...corePackages];
  if (modelOptions[model]?.package) {
    packages.push(modelOptions[model].package);
  }

  // Initialize and configure.
  if (isNew) {
    const answer = await inquirer.prompt<{ module: string }>([
      {
        type: 'input',
        name: 'module',
        message:
          'Enter the Go module name (e.g. github.com/user/genkit-go-app):',
      },
    ]);
    try {
      execSync(`go mod init ${answer.module}`, { stdio: 'ignore' });
    } catch (err) {
      logger.error(`Failed to initialize Go project: ${err}`);
      process.exit(1);
    }
  }
  installPackages(packages);
  if (
    options.nonInteractive ||
    (await confirm({
      message: 'Would you like to generate a sample flow?',
      default: true,
    }))
  ) {
    await generateSampleFile(model);
  }

  showModelInfo(model);

  // Record event.
  await record(new InitEvent('go'));
}

/**
 * Installs Go Packages.
 */
function installPackages(packages: string[]) {
  const spinner = ora('Installing Go packages').start();
  try {
    execSync(`go get ${packages.map((p) => p + '@v0.1').join(' ')}`, {
      stdio: 'ignore',
    });
    spinner.succeed('Successfully installed Go packages');
  } catch (err) {
    spinner.fail(`Error installing packages: ${err}`);
    process.exit(1);
  }
}

/**
 * Generates a sample main.go file.
 */
async function generateSampleFile(model: ModelProvider) {
  let filename = 'main.go';
  let samplePath = path.join(process.cwd(), filename);
  let write = true;
  if (fs.existsSync(samplePath)) {
    filename = 'genkit.go';
    samplePath = path.join(process.cwd(), filename);
    if (fs.existsSync(samplePath)) {
      write = await confirm({
        message: `${filename} already exists. Would you like to overwrite it?`,
        default: false,
      });
    }
  }
  const spinner = ora('Generating sample file').start();
  try {
    const fullPath = path.join(__dirname, templatePath);
    let sample = fs.readFileSync(fullPath, 'utf8');
    const modelOption = modelOptions[model];
    sample = sample
      .replace(
        '$GENKIT_FUNC_NAME',
        filename === 'genkit.go' ? 'initGenkit' : 'main'
      )
      .replace(
        '$GENKIT_MODEL_IMPORT',
        modelOption.package
          ? `\n\t// Import the ${modelOption.label} plugin.\n\t"${modelOption.package}"`
          : ''
      )
      .replace('$GENKIT_MODEL_INIT', modelOption.init)
      .replace('$GENKIT_MODEL_LOOKUP', modelOption.lookup);
    if (write) {
      fs.writeFileSync(samplePath, sample, 'utf8');
      spinner.succeed(`Successfully generated sample file (${filename})`);
    } else {
      spinner.warn('Skipped generating sample file');
    }
  } catch (err) {
    spinner.fail(`Failed to generate sample file: ${err}`);
    process.exit(1);
  }
}
