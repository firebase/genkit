import {
  SupportedFlagValues,
  ToolPlugin,
  cliCommand,
  promptContinue,
} from '@genkit-ai/tools-plugins/plugins';
import * as clc from 'colorette';

export const GoogleCloudTools: ToolPlugin = {
  name: 'Google Cloud',
  keyword: 'google',
  actions: [
    {
      action: 'use-app-default-creds',
      helpText:
        'Logs into Google and downloads application default credentials file',
      args: [
        {
          flag: '--project <project-id>',
          description: 'GCP project to use; required',
        },
      ],
      hook: useApplicationDefaultCredentials,
    },
  ],
  subCommands: {
    login: {
      hook: login,
    },
  },
};

async function login(): Promise<void> {
  const cont = await promptContinue(
    'Genkit will use the GCloud CLI to log in to your Google account ' +
      'using OAuth, in order to perform administrative tasks',
    true
  );
  if (!cont) return;

  try {
    cliCommand('gcloud', `auth login`);
  } catch (e) {
    errorMessage(
      'Unable to complete login. Make sure the gcloud CLI is ' +
        `installed and you're able to open a browser.`
    );
    return;
  }

  console.log(`${clc.bold('Successfully signed in to GCloud.')}`);
}

async function useApplicationDefaultCredentials(
  opts?: Record<string, SupportedFlagValues>
): Promise<void> {
  const project = opts?.project;

  if (!project || typeof project !== 'string') {
    errorMessage(
      'Project not specified. Provide a project ID using the --project flag'
    );
    return;
  }

  const cont = await promptContinue(
    'Genkit will use the GCloud CLI to log in to Google and download ' +
      `application default credentials for your project: ${clc.bold(project)}.`,
    true
  );
  if (!cont) return;

  try {
    // Always supply the project ID so that we don't accidentally use the last-
    // specified project ID configured with GCloud. Doing so may cause
    // confusion since we're wrapping GCloud.
    cliCommand('gcloud', `auth application-default login --project=${project}`);
  } catch (e) {
    errorMessage(
      'Unable to complete login. Make sure the gcloud CLI is ' +
        `installed and you're able to open a browser.`
    );
    return;
  }

  console.log(
    `${clc.bold(
      'Successfully signed in using application-default credentials.'
    )}`
  );
  console.log(
    'Goole Cloud SDKs will now automatically pick up your credentials during development.'
  );
}

function errorMessage(msg: string): void {
  console.error(clc.bold(clc.red('Error:')) + ' ' + msg);
}
