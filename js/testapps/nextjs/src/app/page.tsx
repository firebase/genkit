'use client';

import { tellJoke } from '@/genkit/joke';
import { runFlow, streamFlow } from '@genkit-ai/nextjs/client';
import { useEffect, useRef, useState } from 'react';

async function run(type: string, setResponse: (response: string) => void) {
  setResponse('...');
  const resp = await runFlow<typeof tellJoke>('/api/joke', type);
  setResponse(resp);
}

async function stream(type: string, setResponse: (response: string) => void) {
  let accum = '';
  setResponse('...');
  const { stream, response } = streamFlow<typeof tellJoke>(
    '/api/joke',
    type === '' ? null : type
  );
  for await (const chunk of stream) {
    accum = accum + chunk;
    setResponse(accum);
  }
  setResponse(await response);
}

export default function Home() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [getResponse, setResponse] = useState<string>('');
  function focus() {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }
  useEffect(focus);
  return (
    <>
      <div>
        <input type="text" alt="Joke type" ref={inputRef}></input>
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
      <div>getRespone()</div>
    </>
  );
}
