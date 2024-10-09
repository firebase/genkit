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

import { ModelAction } from 'genkit/model';
import { GoogleAuth } from 'google-auth-library';
import { PluginOptions } from '..';

let imagenModel;
let SUPPORTED_IMAGEN_MODELS: Record<string, { name: string }> = {};

let imagen2;
let imagen3;
let imagen3Fast;

export default async function vertexAiImagen(
  projectId: string,
  location: string,
  options: PluginOptions | undefined,
  authClient: GoogleAuth
): Promise<ModelAction<any>[]> {
  await initalizeDependencies();

  const imagenModels = Object.keys(SUPPORTED_IMAGEN_MODELS).map((name) =>
    imagenModel(name, authClient, { projectId, location })
  );

  return imagenModels;
}

async function initalizeDependencies() {
  const {
    imagen2: imagen2Import,
    imagen3: imagen3Import,
    imagen3Fast: imagen3FastImport,
    imagenModel: imagenModelImport,
    SUPPORTED_IMAGEN_MODELS: SUPPORTED_IMAGEN_MODELS_IMPORT,
  } = await import('./imagen.js');

  imagen2 = imagen2Import;
  imagen3 = imagen3Import;
  imagen3Fast = imagen3FastImport;
  imagenModel = imagenModelImport;
  SUPPORTED_IMAGEN_MODELS = SUPPORTED_IMAGEN_MODELS_IMPORT;
}

export { imagen2, imagen3, imagen3Fast };
