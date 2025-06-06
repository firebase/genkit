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
import { logger } from 'genkit/logging';
import { GoogleAuth, auth, type CredentialBody } from 'google-auth-library';
import type { GcpPrincipal, GcpTelemetryConfig } from './types.js';

/**
 * Allows Google Cloud credentials to be to passed in "raw" as an environment
 * variable. This is helpful in environments where the developer has limited
 * ability to configure their compute environment, but does have the ablilty to
 * set environment variables.
 *
 * This is different from the GOOGLE_APPLICATION_CREDENTIALS used by ADC, which
 * represents a path to a credential file on disk. In *most* cases, even for
 * 3rd party cloud providers, developers *should* attempt to use ADC, which
 * searches for credential files in standard locations, before using this
 * method.
 *
 * See also: https://github.com/googleapis/google-auth-library-nodejs?tab=readme-ov-file#loading-credentials-from-environment-variables
 */
export async function credentialsFromEnvironment(): Promise<
  Partial<GcpTelemetryConfig>
> {
  let authClient: GoogleAuth;
  const options: Partial<GcpTelemetryConfig> = {};

  if (process.env.GCLOUD_SERVICE_ACCOUNT_CREDS) {
    logger.debug('Retrieving credentials from GCLOUD_SERVICE_ACCOUNT_CREDS');
    const serviceAccountCreds = JSON.parse(
      process.env.GCLOUD_SERVICE_ACCOUNT_CREDS
    );
    const authOptions = { credentials: serviceAccountCreds };
    authClient = new GoogleAuth(authOptions);
    options.credentials = await authClient.getCredentials();
  } else {
    authClient = new GoogleAuth();
  }
  try {
    const projectId = await authClient.getProjectId();
    if (projectId && projectId.length > 0) {
      options.projectId = projectId;
    }
  } catch (error) {
    logger.warn(error);
  }
  return options;
}

/**
 * Resolve the currently configured principal, either from the Genkit specific
 * GCLOUD_SERVICE_ACCOUNT_CREDS environment variable, or from ADC.
 *
 * Since the Google Cloud Telemetry Exporter will discover credentials on its
 * own, we don't immediately have access to the current principal. This method
 * can be handy to get access to the current credential for logging debugging
 * information or other purposes.
 **/
export async function resolveCurrentPrincipal(): Promise<GcpPrincipal> {
  const envCredentials = await credentialsFromEnvironment();
  let adcCredentials = {} as CredentialBody;
  try {
    adcCredentials = await auth.getCredentials();
  } catch (e) {
    logger.debug('Could not retrieve client_email from ADC.');
  }

  // TODO(michaeldoyle): How to look up if the user provided credentials in the
  // plugin config (i.e. GcpTelemetryOptions)
  const serviceAccountEmail =
    envCredentials.credentials?.client_email ?? adcCredentials.client_email;

  return {
    projectId: envCredentials.projectId,
    serviceAccountEmail,
  };
}
