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

import { GoogleAuth } from 'google-auth-library';
import { google } from 'googleapis';

export async function getAccessToken(auth: GoogleAuth) {
  const client = await auth.getClient();
  const _accessToken = await client.getAccessToken();
  return _accessToken.token;
}

export async function getProjectNumber(projectId: string): Promise<string> {
  const client = google.cloudresourcemanager('v1');
  const authClient = await google.auth.getClient({
    scopes: ['https://www.googleapis.com/auth/cloud-platform'],
  });

  try {
    const response = await client.projects.get({
      projectId: projectId,
      auth: authClient,
    });

    if (!response.data.projectNumber) {
      throw new Error(
        `Error fetching project number for Vertex AI plugin for project ${projectId}`
      );
    }
    return response.data['projectNumber'];
  } catch (error) {
    // console.error('Error fetching project number:', error);
    throw new Error(
      `Error fetching project number for Vertex AI plugin for project ${projectId}`
    );
  }
}
