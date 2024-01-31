import { getFunctions } from 'firebase-admin/functions';
import { GoogleAuth } from 'google-auth-library';
import { FlowInvokeEnvelopeMessage } from './types';

/**
 * Sends the flow invocation envelope to the flow via a task queue.
 */
export async function dispatchCloudTask(
  flowName: string,
  payload: FlowInvokeEnvelopeMessage,
  scheduleDelaySeconds = 0
) {
  const queue = getFunctions().taskQueue(flowName);
  const targetUri = await getFunctionUrl(flowName);
  console.log('targetUri', targetUri);
  await queue.enqueue(payload, {
    scheduleDelaySeconds,
    dispatchDeadlineSeconds: 60 * 5, // 5 minutes
    uri: targetUri,
  });
}

let auth;
async function getFunctionUrl(name, location = 'us-central1') {
  if (!auth) {
    auth = new GoogleAuth({
      scopes: 'https://www.googleapis.com/auth/cloud-platform',
    });
  }
  const projectId = await auth.getProjectId();
  const url =
    'https://cloudfunctions.googleapis.com/v2beta/' +
    `projects/${projectId}/locations/${location}/functions/${name}`;

  const client = await auth.getClient();
  const res = await client.request({ url });
  const uri = res.data?.serviceConfig?.uri;
  if (!uri) {
    throw new Error(`Unable to retreive uri for function at ${url}`);
  }
  return uri;
}
