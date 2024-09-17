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
import { logger } from '@genkit-ai/core/logging';
import { GoogleAuth } from 'google-auth-library';
import { GcpPluginOptions } from './types';

/**
 * Allow customers to pass in cloud credentials from environment variables
 * following: https://github.com/googleapis/google-auth-library-nodejs?tab=readme-ov-file#loading-credentials-from-environment-variables
 */
export async function credentialsFromEnvironment(): Promise<GcpPluginOptions> {
  let authClient: GoogleAuth;
  let options: GcpPluginOptions = {};

  if (process.env.GCLOUD_SERVICE_ACCOUNT_CREDS) {
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
