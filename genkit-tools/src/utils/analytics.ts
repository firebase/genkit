import { createInterface } from 'readline/promises';
import { configstore } from './configstore';

// Analytics are not enabled during EAP. Before public preview, remove this
// comment and the ANALYTICS_ENABLED flag below.

const ANALYTICS_ENABLED = false; // Set to true before public preview.
const ANALYTICS_NOTIFICATION = 'Notice: PLACEHOLDER PLACEHOLDER PLACEHOLDER';
const NOTIFICATION_ACKED = 'analytics_notification';

const readline = createInterface({
  input: process.stdin,
  output: process.stdout,
});

export async function notifyAnalyticsIfFirstRun(): Promise<void> {
  if (!ANALYTICS_ENABLED) return;

  if (configstore.get(NOTIFICATION_ACKED)) {
    return;
  }

  console.log(ANALYTICS_NOTIFICATION);
  await readline.question('(Press Enter to continue)');

  configstore.set(NOTIFICATION_ACKED, true);
}
