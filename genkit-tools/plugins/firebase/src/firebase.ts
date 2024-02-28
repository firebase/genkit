import {
  SupportedFlagValues,
  ToolPlugin,
  cliCommand,
  promptContinue,
} from '@google-genkit/tools-plugins/plugins';
import * as clc from 'colorette';

export const FirebaseTools: ToolPlugin = {
  name: 'Firebase',
  keyword: 'firebase',
  actions: [],
  subCommands: {
    login: {
      hook: login,
      args: [
        {
          flag: '--reauth',
          description: 'Reauthenticate using current credentials',
          defaultValue: false,
        },
      ],
    },
    deploy: {
      hook: deploy,
      args: [
        {
          flag: '--project <project-id>',
          description: 'Project ID to deploy to (optional)',
          defaultValue: '',
        },
      ],
    },
  },
};

async function login(
  args?: Record<string, SupportedFlagValues>
): Promise<void> {
  const cont = await promptContinue(
    'Genkit will use the Firebase Tools CLI to log in to your Google ' +
      'account using OAuth, in order to perform administrative tasks',
    true
  );
  if (!cont) return;

  try {
    cliCommand('firebase', `login ${args?.reauth ? '--reauth' : ''}`);
  } catch (e) {
    errorMessage(
      'Unable to complete login. Make sure the Firebase Tools CLI is ' +
        `installed and you're able to open a browser.`
    );
    return;
  }

  console.log(`${clc.bold('Successfully signed in to Firebase CLI.')}`);
}

async function deploy(
  args?: Record<string, SupportedFlagValues>
): Promise<void> {
  const cont = await promptContinue(
    'Genkit will use the Firebase Tools CLI to deploy your flow to Cloud ' +
      'Functions for Firebase',
    true
  );
  if (!cont) return;

  try {
    cliCommand(
      'firebase',
      `deploy ${args?.project ? '--project ' + args.project : ''}`
    );
  } catch (e) {
    errorMessage(
      'Unable to complete login. Make sure the Firebase Tools CLI is ' +
        `installed and you've already logged in with 'genkit login firebase'. ` +
        'Make sure you have a firebase.json file configured for this project.'
    );
    return;
  }
}

function errorMessage(msg: string): void {
  console.error(clc.bold(clc.red('Error:')) + ' ' + msg);
}
