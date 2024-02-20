import {
  ToolPlugin,
  cliCommand,
  promptContinue,
} from '@google-genkit/tools-plugins/plugins';
import * as clc from 'colorette';

export const GoogleCloudTools: ToolPlugin = {
  name: 'Google Cloud',
  keyword: 'google',
  actions: [
    {
      action: 'login',
      hook: login,
    },
  ],
};

async function login(): Promise<void> {
  const cont = await promptContinue(
    'Genkit will attempt to login to Google using the GCloud CLI tool.',
    true,
  );
  if (!cont) return;

  try {
    cliCommand('gcloud', 'auth application-default login');
  } catch (e) {
    console.error(
      `${clc.bold(
        clc.red('Error:'),
      )} Unable to complete login. Make sure the gcloud CLI is installed and you're able to open a browser.`,
    );
    return;
  }

  console.log(
    `${clc.bold(
      'Successfully signed in using application-default credentials.',
    )}`,
  );
  console.log(
    'Goole Cloud SDKs will now automatically pick up your credentials during development.',
  );
}
