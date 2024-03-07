import { GoogleAuth } from 'google-auth-library';
import { PluginOptions } from '.';

function endpoint(options: {
  projectId: string;
  location: string;
  model: string;
}) {
  // eslint-disable-next-line max-len
  return `https://${options.location}-aiplatform.googleapis.com/v1/projects/${options.projectId}/locations/${options.location}/publishers/google/models/${options.model}:predict`;
}

interface PredictionResponse<R> {
  predictions: R[];
}

export function predictModel<I = unknown, R = unknown, P = unknown>(
  auth: GoogleAuth,
  { location, projectId }: PluginOptions,
  model: string
) {
  return async (
    instances: I[],
    parameters?: P
  ): Promise<PredictionResponse<R>> => {
    const fetch = (await import('node-fetch')).default;
    // TODO: Don't do it this way.
    const accessToken = await (
      await auth.getApplicationDefault()
    ).credential.getAccessToken();

    const req = {
      instances,
      parameters: parameters || {},
    };

    const response = await fetch(
      endpoint({
        projectId: projectId!,
        location,
        model,
      }),
      {
        method: 'POST',
        body: JSON.stringify(req),
        headers: {
          Authorization: `Bearer ${accessToken.token}`,
          'Content-Type': 'application/json',
          'User-Agent': 'genkit',
        },
      }
    );

    if (!response.ok) {
      throw new Error(
        `Error from Vertex AI predict: HTTP ${
          response.status
        }: ${await response.text()}`
      );
    }

    return (await response.json()) as PredictionResponse<R>;
  };
}
