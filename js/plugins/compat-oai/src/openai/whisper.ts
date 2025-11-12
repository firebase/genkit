/**
 * Copyright 2024 The Fire Company
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

import { compatOaiTranscriptionModelRef as openAITranscriptionModelRef } from '../audio';

/** OpenAI transcription ModelRef helper, same as the OpenAI-compatible spec. */
export { openAITranscriptionModelRef };

export const SUPPORTED_STT_MODELS = {
  'gpt-4o-transcribe': openAITranscriptionModelRef({
    name: 'openai/gpt-4o-transcribe',
  }),
  'whisper-1': openAITranscriptionModelRef({ name: 'openai/whisper-1' }),
};
