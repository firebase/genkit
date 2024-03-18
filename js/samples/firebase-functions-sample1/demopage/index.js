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

import {
  GoogleAuthProvider,
  connectAuthEmulator,
  getAuth,
  signInAnonymously,
  signInWithPopup,
} from 'firebase/auth';
import { initializeApp } from 'firebase/app';
import {
  connectFunctionsEmulator,
  getFunctions,
  httpsCallable,
} from 'firebase/functions';

import $ from 'jquery';

// This code assumes `firebaseConfig` is a global variable containing
// your Firebase configuration object. You can get this object from the
// Firebase console by adding a web app and copying the blob. Put that
// blob in public/config.js with the following:
//    window.firebaseConfig = {...};

let auth;
let jokeFlow;
let emulated = false;

async function getDecodedIdToken() {
  const tok = await auth.currentUser.getIdToken();
  const [, claims] = tok.split('.');
  return JSON.stringify(JSON.parse(atob(claims)), null, 2);
}

function updateResult(message, code) {
  $('#response').text(message);
  $('#response-code').text(code);
}

$(() => {
  emulated = new URL(window.location.href).search.includes('emulated=true');
  initializeApp(window.firebaseConfig);
  auth = getAuth();
  const fns = getFunctions();

  if (emulated) {
    $('#emulator-button').text('Use prod');
    $('#emulator-warning').show();
    connectAuthEmulator(auth, 'http://localhost:9099', {
      disableWarnings: true,
    });
    connectFunctionsEmulator(fns, 'localhost', 5001);
  }

  jokeFlow = httpsCallable(fns, 'jokeFlow');
  auth.onAuthStateChanged(async (user) => {
    if (user) {
      $('#login').hide();
      $('#logout').show();
      $('#token-blob').text(await getDecodedIdToken());
      console.log(await auth.currentUser.getIdToken());
    } else {
      $('#login').show();
      $('#logout').hide();
      $('#token-blob').text('Signed out');
    }
  });
});

window.anonymous = async () => {
  await signInAnonymously(auth);
};

window.google = async () => {
  await signInWithPopup(auth, new GoogleAuthProvider());
};

window.logout = async () => {
  await auth.signOut();
};

window.runflow = async () => {
  try {
    const payload = $('#subject').val();
    const response = await jokeFlow(payload);
    updateResult(response.data.response, '200');
  } catch (e) {
    updateResult(e.message, e.code);
  }
};

window.emulate = function () {
  const url = new URL(window.location.href);
  if (emulated) {
    url.search = '';
  } else {
    url.search = 'emulated=true';
  }
  window.location.replace(url);
};
