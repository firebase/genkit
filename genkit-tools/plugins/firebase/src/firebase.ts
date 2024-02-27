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
  specialActions: {
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
  },
};

async function login(
  args?: Record<string, SupportedFlagValues>
): Promise<void> {
  console.log('here');
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

function errorMessage(msg: string): void {
  console.error(clc.bold(clc.red('Error:')) + ' ' + msg);
}
