// Copyright 2024 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import { GoogleAuth, GoogleAuthOptions } from 'google-auth-library';

const CLOUD_PLATFROM_OAUTH_SCOPE =
  'https://www.googleapis.com/auth/cloud-platform';

/**
 * Authenticate with Google Cloud
 * @param authOptions The authentication options to use.
 * @returns The GoogleAuth object.
 */
export const authenticate: (authOptions?: GoogleAuthOptions) => GoogleAuth = (authOptions?: GoogleAuthOptions) => {
    let authClient;

    // Allow customers to pass in cloud credentials from environment variables
    // following: https://github.com/googleapis/google-auth-library-nodejs?tab=readme-ov-file#loading-credentials-from-environment-variables
    if (process.env.GCLOUD_SERVICE_ACCOUNT_CREDS) {
        const serviceAccountCreds = JSON.parse(
            process.env.GCLOUD_SERVICE_ACCOUNT_CREDS
        );
        authOptions = {
            credentials: serviceAccountCreds,
            scopes: [CLOUD_PLATFROM_OAUTH_SCOPE],
        };
        authClient = new GoogleAuth(authOptions);
    } else {
        authClient = new GoogleAuth(
            authOptions ?? { scopes: [CLOUD_PLATFROM_OAUTH_SCOPE] }
        );
    }

    return authClient;
}