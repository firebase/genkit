import {
  GoogleAuthProvider,
  getAuth,
  signInAnonymously,
  signInWithPopup,
} from 'firebase/auth';
import { initializeApp } from 'firebase/app';
import { getFunctions, httpsCallable } from 'firebase/functions';

import $ from 'jquery';

// This code assumes `firebaseConfig` is a global variable containing
// your Firebase configuration object. You can get this object from the
// Firebase console by adding a web app and copying the blob. Put that
// blob in public/config.js with the following:
//    window.firebaseConfig = {...};

let auth;
let jokeFlow;

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
  initializeApp(window.firebaseConfig);
  auth = getAuth();
  const fns = getFunctions();
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
    const payload = {
      start: {
        input: $('#subject').val(),
      },
    };
    const response = await jokeFlow(payload);
    updateResult(response.data.response, '(success)');
  } catch (e) {
    updateResult(e.code, '(error)');
  }
};
