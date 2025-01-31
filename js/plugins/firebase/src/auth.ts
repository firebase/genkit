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

import { DecodedAppCheckToken, getAppCheck } from 'firebase-admin/app-check';
import { DecodedIdToken, getAuth } from 'firebase-admin/auth';
import {
  Request,
  RequestMiddleware,
  UserFacingError,
} from 'genkit/requestMiddleware';
import { initializeAppIfNecessary } from './helpers.js';

/**
 * Debug features that can be enabled to simplify testing.
 * These features are in a JSON object for FIREBASE_DEBUG_FEATURES and only take
 * effect if FIREBASE_DEBUG_MODE=true.
 *
 * Do not set these variables in production.
 */
export interface DebugFeatures {
  skipTokenVerification?: boolean;
}

let cachedDebugSkipTokenVerification: boolean | undefined;

export function setDebugSkipTokenVerification(skip: boolean) {
  cachedDebugSkipTokenVerification = skip;
}

function debugSkipTokenVerification(): boolean {
  if (cachedDebugSkipTokenVerification !== undefined) {
    return cachedDebugSkipTokenVerification;
  }
  if (!process.env.FIREBASE_DEBUG_MODE) {
    return false;
  }
  if (!process.env.FIREBASE_DEBUG_FEATURES) {
    return false;
  }
  const features = JSON.parse(
    process.env.FIREBASE_DEBUG_FEATURES
  ) as DebugFeatures;
  cachedDebugSkipTokenVerification = features.skipTokenVerification ?? false;
  return cachedDebugSkipTokenVerification;
}

/**
 * The type of data that will be added to an Action's context when using the fireabse middleware.
 * You can safely cast Action's context to a Firebase Context to help type checking and code complete.
 */
export interface FirebaseContext {
  /**
   * Information about the authorized user.
   * This comes from the Authentication header, which is a JWT bearer token.
   * Will be omitted if auth is not defined or the key is invalid. To reject requests in these cases
   * set signedIn in a declarative policy or check in a policy callback.
   */
  auth?: {
    uid: string;
    token: DecodedIdToken;
  };

  /**
   * Information about the AppCheck token for a request.
   * This comes form the X-Firebase-AppCheck header and is included in the firebase-functions
   * client libraries (which can be used for Genkit requests irrespective of whether they're hosted
   * on Firebase).
   * Will be omitted if AppCheck tokens are invalid. To reject requests in these cases,
   * set enforceAppCheck in a declaritve policy or check in a policy callback.
   */
  app?: {
    appId: string;
    token: DecodedAppCheckToken;
    alreadyConsumed?: boolean;
  };

  /**
   * An unverified token for a Firebase Instance ID.
   */
  instanceIdToken?: string;
}

export interface FirebaseMiddleware<I = any> extends RequestMiddleware<I> {
  (request: Request<I>): Promise<FirebaseContext>;
}

/**
 * Helper methods that provide most common needs for an authorization policy.
 */
export interface DeclarativePolicy {
  /**
   * Requires the user to be signed in or not.
   * Implicitly part of hasClaims.
   */
  signedIn?: boolean;

  /**
   * Clam or Claims that must be present in the request.
   * Can be a singel claim name or array of claim names to merely test the presence
   * of a clam or can be an object of claim names and values that must be present.
   */
  hasClaim?: string | string[] | Record<string, string>;

  /**
   * Whether appCheck must be enforced
   */
  enforceAppCheck?: boolean;

  /**
   * Whether app check enforcement includes consuming tokens.
   * Consuming tokens adds more security at the cost of performance.
   */
  consumeAppCheckToken?: boolean;
}

/**
 * Calling firebaseAuth() without any parameters merely parses firebase context data.
 * It does not do any validation on the data found. To do automatic validation,
 * pass either an options object or function for freeform validation.
 */
export function firebaseAuth<I = any>(): FirebaseMiddleware<I>;

/**
 * Calling firebaseAuth() with a declarative policy both parses and enforces context.
 * Honors the same environment variables that Cloud Functions for Firebase does to
 * mock token validation in preproduction environmets.
 */
export function firebaseAuth<I = any>(
  policy: DeclarativePolicy
): FirebaseMiddleware<I>;

/**
 * Calling firebaseAuth() with a policy context parses context but delegates enforcement.
 * To control the message sent to a user, throw UserFacingError from genkit/requestMiddleware.
 * For security reasons, other error types will be returned as a 500 "internal error".
 */
export function firebaseAuth<I = any>(
  policy: (context: FirebaseContext, input: I) => void | Promise<void>
): FirebaseMiddleware<I>;

export function firebaseAuth<I = any>(
  policy?:
    | DeclarativePolicy
    | ((context: FirebaseContext, input: I) => void | Promise<void>)
): FirebaseMiddleware<I> {
  return async function (request: Request): Promise<FirebaseContext> {
    initializeAppIfNecessary();
    const auth = await parseAuth(request.headers['authentication']);
    const consumeAppCheckToken =
      typeof policy === 'object' && policy['consumeAppCheckToken'];
    const app = await parseAppCheck(
      request.headers['x-firebase-appcheck'],
      consumeAppCheckToken ?? false
    );
    const instanceIdToken = request.headers['firebase-instance-id-token'];
    const context: FirebaseContext = {};
    if (auth) {
      context.auth = auth;
    }
    if (app) {
      context.app = app;
    }
    if (instanceIdToken) {
      context.instanceIdToken = instanceIdToken;
    }
    if (typeof policy === 'function') {
      await policy(context, request.body);
    } else if (typeof policy === 'object') {
      enforceDelcarativePolicy(policy, context);
    }
    return context;
  };
}

function enforceDelcarativePolicy(
  policy: DeclarativePolicy,
  context: FirebaseContext
) {
  if ((policy.signedIn || policy.hasClaim) && !context.auth) {
    throw new UserFacingError(401, 'Auth is required');
  }
  if (policy.hasClaim) {
    function verifyHasClaims(claims: string[], token: DecodedIdToken) {
      for (const claim of claims) {
        if (!token[claim]) {
          throw new UserFacingError(403, `${claim} claim is required`);
        }
      }
    }
    if (typeof policy.hasClaim === 'string') {
      verifyHasClaims([policy.hasClaim], context.auth!.token);
    } else if (Array.isArray(policy.hasClaim)) {
      verifyHasClaims(policy.hasClaim, context.auth!.token);
    } else {
      for (const [claim, value] of Object.values(policy.hasClaim)) {
        if (context.auth!.token[claim] !== value) {
          throw new UserFacingError(403, `Claim ${claim} must be ${value}`);
        }
      }
    }
  }
  if (policy.enforceAppCheck && !context.app) {
    throw new UserFacingError(403, `AppCheck token is required`);
  }
}

async function parseAuth(authHeader: string): Promise<FirebaseContext['auth']> {
  const token = /[bB]earer (.*)/.exec(authHeader)?.[1];
  if (!token) {
    return undefined;
  }
  if (debugSkipTokenVerification()) {
    const decoded = unsafeDecodeToken(token) as DecodedIdToken;
    return {
      uid: decoded['sub'],
      token: decoded,
    };
  }
  try {
    const decoded = await getAuth().verifyIdToken(token);
    return {
      uid: decoded['sub'],
      token: decoded,
    };
  } catch (err) {
    console.error(`Error decoding auth token: ${err}`);
    throw new UserFacingError(401, 'Invalid auth token');
  }
}

async function parseAppCheck(
  token: string,
  consumeAppCheckToken: boolean
): Promise<FirebaseContext['app']> {
  if (debugSkipTokenVerification()) {
    const decoded = unsafeDecodeToken(token) as DecodedAppCheckToken;
    return {
      appId: decoded['sub'],
      token: decoded,
      alreadyConsumed: false,
    };
  }
  try {
    return await getAppCheck().verifyToken(token, {
      consume: consumeAppCheckToken,
    });
  } catch (err) {
    console.error(`Got error verifying AppCheck token: ${err}`);
    throw new UserFacingError(403, 'Invalid AppCheck token');
  }
}

export function fakeToken(claims: Record<string, string>): string {
  return `fake.${Buffer.from(JSON.stringify(claims), 'base64').toString()}.fake`;
}

const TOKEN_REGEX = /[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+/;
function unsafeDecodeToken(token: string): Record<string, unknown> {
  if (!TOKEN_REGEX.test(token)) {
    throw UserFacingError(
      401,
      'Invalid fake token. Use the fakeToken() method to create a valid fake token'
    );
  }
  try {
    return JSON.parse(Buffer.from(token.split('.')[1], 'base64').toString());
  } catch (err) {
    throw new UserFacingError(
      410,
      'Invalid fake token. Use the fakeToken() method to create a valid fake token'
    );
  }
}
