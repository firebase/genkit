/**
 * Copyright 2025 Google LLC
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

import { GoogleAuth } from 'google-auth-library';

/**
 * Get email address associated with current authenticated IAM principal.
 * Email will be used for automatic IAM database authentication to Cloud SQL.
 *
 * @param {GoogleAuth} auth - object to use in finding the associated IAM principal email address.
 * @returns {string} email - email address associated with the current authenticated IAM principal
 */
export const getIAMPrincipalEmail = async (
  auth: GoogleAuth
): Promise<string> => {
  const credentials = await auth.getCredentials();

  if ('client_email' in credentials && credentials.client_email !== undefined) {
    return credentials.client_email.replace('.gserviceaccount.com', '');
  }

  const accessToken = await auth.getAccessToken();
  const client = await auth.getClient();

  const url = `https://oauth2.googleapis.com/tokeninfo?access_token=${accessToken}`;
  const clientResponse = await client
    .request({ url })
    .then((res: { data: any }) => res.data);

  if (!('email' in clientResponse)) {
    throw new Error(
      "Failed to automatically obtain authenticated IAM principal's " +
        "email address using environment's ADC credentials!"
    );
  }
  const email = clientResponse['email'];
  return email.replace('.gserviceaccount.com', '');
};
