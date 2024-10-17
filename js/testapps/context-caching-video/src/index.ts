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

import { gemini15Flash, googleAI } from '@genkit-ai/googleai';
import { GoogleAIFileManager } from '@google/generative-ai/server';
import * as fs from 'fs';
import { generate, genkit, z } from 'genkit';
const ai = genkit({
  plugins: [googleAI()],
});

// Utility to check if a video file exists
const checkIfVideoFileExists = async (filePath: string) => {
  try {
    await fs.promises.access(filePath);
    return true;
  } catch {
    return false;
  }
};

// Flow for video file upload
export const videoUploadFlow = ai.defineFlow(
  {
    name: 'videoUploadFlow',
    inputSchema: z.object({
      videoFilePath: z.string(),
    }),
    outputSchema: z.object({
      fileUri: z.string(),
    }),
  },
  async ({ videoFilePath }) => {
    const exists = await checkIfVideoFileExists(videoFilePath);

    if (!exists) {
      throw new Error('Video file does not exist');
    }

    // Initialize the file manager for Gemini API
    const fileManager = new GoogleAIFileManager(
      process.env.GOOGLE_GENAI_API_KEY!
    );

    // Upload video to Google AI using the Gemini Files API
    const uploadResult = await fileManager.uploadFile(videoFilePath, {
      mimeType: 'video/mp4', // Adjust according to the video format
      displayName: 'Uploaded Video for Analysis',
    });

    console.log('Video uploaded successfully:', uploadResult.file.uri);

    return {
      fileUri: uploadResult.file.uri,
    };
  }
);

// Flow for video analysis
export const videoAnalysisFlow = ai.defineFlow(
  {
    name: 'videoAnalysisFlow',
    inputSchema: z.object({
      query: z.string().optional(),
      videoUri: z.string(), // Use the uploaded file URI
    }),
    outputSchema: z.string(),
  },
  async ({ query, videoUri }) => {
    // Video analysis response
    const analyzeVideoResponse = await generate({
      messages: [
        {
          role: 'user',
          content: [
            {
              media: {
                url: videoUri, // Use the uploaded file URL
                contentType: 'video/mp4',
              },
            },
          ],
        },
        {
          role: 'model',
          content: [
            {
              text: 'This video seems to contain several key moments. I will analyze it now and prepare to answer your questions.',
            },
          ],
          // MessageSchema has no generics for extension, is it possible to add one, like we do for generate config?
          metadata: {
            cache: true,
          },
        },
      ],
      config: {
        version: 'gemini-1.5-flash-001', // Adjust based on the correct model version
      },
      model: gemini15Flash,
      prompt: query,
    });

    return analyzeVideoResponse.text();
  }
);
