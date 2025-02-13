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

import * as td from 'typedoc';

export function load(app) {
  app.options.addDeclaration({
    name: 'gaID',
    help: 'Set the Google Analytics tracking ID and activate tracking code',
    type: td.ParameterType.String,
  });

  app.renderer.hooks.on('body.end', () => {
    const gaID = app.options.getValue('gaID');
    if (gaID) {
      const script = `
window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
gtag('js', new Date());
gtag('config', '${gaID}');
const gaAck = localStorage.getItem("gaAck");
if (gaAck !== 'true') {
  var bannerRoot = document.createElement( 'div' );
  bannerRoot.setAttribute('id', 'gaBanner');
  bannerRoot.setAttribute('style', 'border: 1px solid #CCC; padding: 15px 10px; background: white; color: black; text-align: center; position: fixed; bottom: 0px; width: 100%;');
  bannerRoot.innerHTML = 'genkit.dev uses <a href="https://policies.google.com/technologies/cookies">cookies</a> from Google to deliver and enhance the quality of its services and to analyze traffic &nbsp;&nbsp;<button onclick="document.genkitAckGaBanner()">I Understand</button>';
  document.body.appendChild(bannerRoot);
  document.genkitAckGaBanner = function() {
    localStorage.setItem("gaAck", 'true');
    document.getElementById('gaBanner').remove();
  }
}
`.trim();
      return td.JSX.createElement(td.JSX.Fragment, null, [
        td.JSX.createElement('script', {
          async: true,
          src: 'https://www.googletagmanager.com/gtag/js?id=' + gaID,
        }),
        td.JSX.createElement(
          'script',
          null,
          td.JSX.createElement(td.JSX.Raw, { html: script })
        ),
      ]);
    }
    return td.JSX.createElement(td.JSX.Fragment, null);
  });
}
