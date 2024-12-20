import { beforeAll, describe, expect, it } from '@jest/globals';
import { GoogleAuth } from 'google-auth-library';

const TRACE_ID_HEADER = 'x-genkit-trace-id';

const EXPECTED_LOG_MESSAGES = [
  {
    message:
      '[genkit] Config[menuSuggestionFlow > generate > googleai/gemini-1.5-flash, googleai/gemini-1.5-flash]',
    metadata: {
      featureName: 'menuSuggestionFlow',
      model: 'googleai/gemini-1.5-flash',
      path: 'menuSuggestionFlow > generate > googleai/gemini-1.5-flash',
      qualifiedPath:
        '/{menuSuggestionFlow,t:flow}/{generate,t:helper}/{googleai/gemini-1.5-flash,t:action,s:model}',
    },
  },
  {
    message:
      '[genkit] Input[menuSuggestionFlow > generate > googleai/gemini-1.5-flash, googleai/gemini-1.5-flash] ',
    metadata: {
      content: expect.any(String),
      featureName: 'menuSuggestionFlow',
      messageIndex: 0,
      model: 'googleai/gemini-1.5-flash',
      partIndex: 0,
      path: 'menuSuggestionFlow > generate > googleai/gemini-1.5-flash',
      qualifiedPath:
        '/{menuSuggestionFlow,t:flow}/{generate,t:helper}/{googleai/gemini-1.5-flash,t:action,s:model}',
      totalMessages: 1,
      totalParts: 1,
    },
  },
  {
    message:
      '[genkit] Output[menuSuggestionFlow > generate > googleai/gemini-1.5-flash, googleai/gemini-1.5-flash] ',
    metadata: {
      content: expect.any(String),
      candidateIndex: 0,
      featureName: 'menuSuggestionFlow',
      messageIndex: 0,
      model: 'googleai/gemini-1.5-flash',
      partIndex: 0,
      path: 'menuSuggestionFlow > generate > googleai/gemini-1.5-flash',
      qualifiedPath:
        '/{menuSuggestionFlow,t:flow}/{generate,t:helper}/{googleai/gemini-1.5-flash,t:action,s:model}',
      totalCandidates: 1,
      totalParts: 1,
    },
  },
  {
    message: '[genkit] Input[menuSuggestionFlow, menuSuggestionFlow]',
    metadata: {
      content: expect.any(String),
      featureName: 'menuSuggestionFlow',
      path: 'menuSuggestionFlow',
      qualifiedPath: '/{menuSuggestionFlow,t:flow}',
    },
  },
  {
    message: '[genkit] Output[menuSuggestionFlow, menuSuggestionFlow]',
    metadata: {
      content: expect.any(String),
      featureName: 'menuSuggestionFlow',
      path: 'menuSuggestionFlow',
      qualifiedPath: '/{menuSuggestionFlow,t:flow}',
    },
  },
  {
    message: '[genkit] Paths[menuSuggestionFlow]',
    metadata: {
      flowName: 'menuSuggestionFlow',
      paths: ['menuSuggestionFlow > generate > googleai/gemini-1.5-flash'],
    },
  },
].sort(sortByMessage);

interface PayloadWithMessage {
  message: string;
}

async function sleep(millis: number) {
  return new Promise((resolve) => setTimeout(resolve, millis));
}

function sortByMessage(
  payloadA: PayloadWithMessage,
  payloadB: PayloadWithMessage
): number {
  if (payloadA.message < payloadB.message) {
    return -1;
  }

  if (payloadA.message > payloadB.message) {
    return 1;
  }

  return 0;
}

async function fetchLogsForTrace(auth: GoogleAuth, traceId: string) {
  const url: string = 'https://logging.googleapis.com';
  console.log(auth.getAccessToken);
  const logsTokenClient = await auth.getIdTokenClient(url);
  const token = await logsTokenClient.idTokenProvider.fetchIdToken(url);

  const projectId = await auth.getProjectId();

  const logsFilterEnd = new Date(Date.now() + 60_000 * 60 * 24).toISOString();
  const logsFilterStart = new Date(Date.now() - 60_000 * 60 * 24).toISOString();
  console.log(
    `FILTER: (trace="projects/${projectId}/traces/${traceId}" AND timestamp >= "${logsFilterStart}" AND timestamp <= "${logsFilterEnd}")`
  );
  console.log(`Token: ${token}`);
  const requestBody = {
    projectIds: [projectId],
    filter: `(trace="projects/${projectId}/traces/${traceId}" AND timestamp >= "${logsFilterStart}" AND timestamp <= "${logsFilterEnd}")`,
  };
  // fetch cloud logs
  const response = await fetch(url + '/v2/entries:list', {
    method: 'POST',
    body: JSON.stringify(requestBody),
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
  });
  console.log(`Status: ${response.status}, Body: ${await response.text()}`);
  // const response = await logsTokenClient.request({ url, headers: { "Content-Type": "application/json" }, method: 'POST', body: requestBody });
  const logResponse = JSON.parse(await response.text());
  return logResponse.entries
    .map((entry) => entry.jsonPayload)
    .sort(sortByMessage);
}

async function callMenuFunction(
  auth: GoogleAuth,
  url: string,
  subject: string
) {
  const menuFunctionClient = await auth.getIdTokenClient(url);

  if (!menuFunctionClient) {
    throw new Error('Menu function client did not initialize correctly.');
  }

  const payload = { data: { subject } };
  return await menuFunctionClient.request({
    url,
    headers: { 'Content-Type': 'application/json' },
    method: 'POST',
    data: JSON.stringify(payload),
  });
}

describe('Firebase Functions with CommonJS', () => {
  var auth: GoogleAuth;

  beforeAll(() => {
    if (!process.env.GOOGLE_APPLICATION_CREDENTIALS) {
      throw new Error(
        'Service account credentials are required to run e2e tests. Set GOOGLE_APPLICATION_CREDENTIALS to a valid file location.'
      );
    }

    auth = new GoogleAuth();
  });

  it.only('should fetch logs', async () => {
    const payloadEntries = await fetchLogsForTrace(
      auth,
      'cec7315ccb9d54ad776f26e4df7b88c7'
    );
    expect(payloadEntries.length).toEqual(EXPECTED_LOG_MESSAGES.length);
    expect(payloadEntries).toMatchObject(EXPECTED_LOG_MESSAGES);
  });

  it('should run and validate the menuSuggestionFlow function', async () => {
    if (!process.env.MENU_FUNCTION_URL) {
      throw new Error(
        'Set MENU_FUNCTION_URL to the deployed menuSuggestionFlow url.'
      );
    }
    const menuUrl: string = process.env.MENU_FUNCTION_URL;
    const projectId = await auth.getProjectId();

    const loggingUrl: string = 'https://logging.googleapis.com/v2/entries:list';

    // const menuFunctionClient = await auth.getIdTokenClient(url);

    // if (!menuFunctionClient) {
    //   throw new Error("Menu function client did not initialize correctly.");
    // }

    // const payload = { data: { subject: "Pirates" } };
    //const response =  await menuFunctionClient.request({ url, headers: { "Content-Type": "application/json"}, method: 'POST', data: JSON.stringify(payload) });
    const response = await callMenuFunction(auth, menuUrl, 'Pirates');
    const traceId = response.headers[TRACE_ID_HEADER];
    const status = response.status;
    const content = response.data;

    expect(traceId).not.toBeUndefined();
    expect(content).not.toBeUndefined();
    expect(status).toBe(200);

    console.log(`TRACE: ${traceId} PROJECT: ${projectId}`);

    // wait for metrics export interval set to 5_000
    await sleep(10_000);

    // fetch cloud logs
    // const payloadEntries = await fetchLogsForTrace(logging, projectId, traceId);
    // expect(payloadEntries.length).toEqual(EXPECTED_LOG_MESSAGES.length);
    // expect(payloadEntries).toMatchObject(EXPECTED_LOG_MESSAGES);

    // fetch cloud trace

    // fetch cloud metrics
  }, 30_000);
});
