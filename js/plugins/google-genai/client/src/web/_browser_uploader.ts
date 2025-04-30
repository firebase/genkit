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

import { ApiClient } from '../_api_client';
import { FileStat, Uploader } from '../_uploader';
import { getBlobStat, uploadBlob } from '../cross/_cross_uploader';
import { File } from '../types';

export class BrowserUploader implements Uploader {
  async upload(
    file: string | Blob,
    uploadUrl: string,
    apiClient: ApiClient
  ): Promise<File> {
    if (typeof file === 'string') {
      throw new Error('File path is not supported in browser uploader.');
    }

    return await uploadBlob(file, uploadUrl, apiClient);
  }

  async stat(file: string | Blob): Promise<FileStat> {
    if (typeof file === 'string') {
      throw new Error('File path is not supported in browser uploader.');
    } else {
      return await getBlobStat(file);
    }
  }
}
