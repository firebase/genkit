'use client';

import { tellJoke } from '@/genkit/joke';
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
