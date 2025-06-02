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
 *
 * SPDX-License-Identifier: Apache-2.0
 */

'use client';

import type { tellJoke } from '@/genkit/joke';
import { runFlow, streamFlow } from '@genkit-ai/next/client';
import { useEffect, useRef, useState } from 'react';
import styles from './page.module.css';

async function run(type: string, setResponse: (response: string) => void) {
  setResponse('...');
  const resp = await runFlow<typeof tellJoke>({
    url: '/api/joke',
    input: type === '' ? null : type,
  });
  setResponse(resp);
}

async function stream(type: string, setResponse: (response: string) => void) {
  let accum = '';
  setResponse('...');
  const { stream, output } = streamFlow<typeof tellJoke>({
    url: '/api/joke',
    input: type === '' ? null : type,
  });
  for await (const chunk of stream) {
    accum = accum + chunk;
    setResponse(accum);
  }
  setResponse(await output);
}

export default function Home() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [response, setResponse] = useState<string>('Pick a joke type');
  function focus() {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }
  useEffect(focus);
  return (
    <>
      <div className={styles.title}>
        <input
          type="text"
          alt="Joke type"
          placeholder="Joke type"
          ref={inputRef}></input>
        <button
          onClick={() => {
            run(inputRef.current!.value, setResponse);
            focus();
          }}>
          Run
        </button>
        <button
          onClick={() => {
            stream(inputRef.current!.value, setResponse);
            focus();
          }}>
          Stream
        </button>
      </div>
      <div>{response}</div>
    </>
  );
}
