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
 */

/**
 * A universal type that request handling extensions (e.g. express, next) can map their request to.
 * This allows middleware to build consistent interfacese on any web framework.
 * Headers must be lowercase to ensure portability.
 */
export interface Request<T = any> {
  method: 'GET' | 'PUT' | 'POST' | 'DELETE' | 'OPTIONS' | 'QUERY';
  headers: Record<string, string>;
  body: T;
}

// Copied from firebase-functions/common/providers/https.ts which is the
// current canonical source for the Callable protocol.
export type ErrorCode =
  | 'ok'
  | 'cancelled'
  | 'unknown'
  | 'invalid-argument'
  | 'deadline-exceeded'
  | 'not-found'
  | 'already-exists'
  | 'permission-denied'
  | 'resource-exhausted'
  | 'failed-precondition'
  | 'aborted'
  | 'out-of-range'
  | 'unimplemented'
  | 'internal'
  | 'unavailable'
  | 'data-loss'
  | 'unauthenticated';

export type CanonicalErrorCodeName =
  | 'OK'
  | 'CANCELLED'
  | 'UNKNOWN'
  | 'INVALID_ARGUMENT'
  | 'DEADLINE_EXCEEDED'
  | 'NOT_FOUND'
  | 'ALREADY_EXISTS'
  | 'PERMISSION_DENIED'
  | 'UNAUTHENTICATED'
  | 'RESOURCE_EXHAUSTED'
  | 'FAILED_PRECONDITION'
  | 'ABORTED'
  | 'OUT_OF_RANGE'
  | 'UNIMPLEMENTED'
  | 'INTERNAL'
  | 'UNAVAILABLE'
  | 'DATA_LOSS';

interface HttpErrorCode {
  canonicalName: CanonicalErrorCodeName;
  status: number;
}

const errorCodeMap: { [name in ErrorCode]: HttpErrorCode } = {
  ok: { canonicalName: 'OK', status: 200 },
  cancelled: { canonicalName: 'CANCELLED', status: 499 },
  unknown: { canonicalName: 'UNKNOWN', status: 500 },
  'invalid-argument': { canonicalName: 'INVALID_ARGUMENT', status: 400 },
  'deadline-exceeded': { canonicalName: 'DEADLINE_EXCEEDED', status: 504 },
  'not-found': { canonicalName: 'NOT_FOUND', status: 404 },
  'already-exists': { canonicalName: 'ALREADY_EXISTS', status: 409 },
  'permission-denied': { canonicalName: 'PERMISSION_DENIED', status: 403 },
  unauthenticated: { canonicalName: 'UNAUTHENTICATED', status: 401 },
  'resource-exhausted': { canonicalName: 'RESOURCE_EXHAUSTED', status: 429 },
  'failed-precondition': { canonicalName: 'FAILED_PRECONDITION', status: 400 },
  aborted: { canonicalName: 'ABORTED', status: 409 },
  'out-of-range': { canonicalName: 'OUT_OF_RANGE', status: 400 },
  unimplemented: { canonicalName: 'UNIMPLEMENTED', status: 501 },
  internal: { canonicalName: 'INTERNAL', status: 500 },
  unavailable: { canonicalName: 'UNAVAILABLE', status: 503 },
  'data-loss': { canonicalName: 'DATA_LOSS', status: 500 },
};

interface HttpErrorWireFormat {
  details?: unknown;
  message: string;
  status: CanonicalErrorCodeName;
}

/**
 * Creates a new class of Error for issues to be returned to users.
 * Using this error allows a web framework handler (e.g. express, next) to know it
 * is safe to return the message in a request. Other kinds of errors will
 * result in a generic 500 message to avoid the possibility of internal
 * exceptions being leaked to attackers.
 * In JSON requests, code will be an HTTP code and error will be a response body.
 * In streaming requests, { code, message } will be passed as the error message.
 */
export class UserFacingError extends Error {
  /**
   * A standard error code that will be returned to the client. This also
   * determines the HTTP status code of the response, as defined in code.proto.
   */
  public readonly code: ErrorCode;

  /**
   * Extra data to be converted to JSON and included in the error response.
   */
  public readonly details: unknown;

  /**
   * A wire format representation of a provided error code.
   */
  public readonly httpErrorCode: HttpErrorCode;

  constructor(code: ErrorCode, message: string, details?: unknown) {
    super(message);

    // A sanity check for non-TypeScript consumers.
    if (code in errorCodeMap === false) {
      throw new Error(`Unknown error code: ${code}.`);
    }

    this.code = code;
    this.details = details;
    this.httpErrorCode = errorCodeMap[code];
  }

  /**
   * Returns a JSON-serializable representation of this object.
   */
  public toJSON(): HttpErrorWireFormat {
    const {
      details,
      httpErrorCode: { canonicalName: status },
      message,
    } = this;

    return {
      ...(details === undefined ? {} : { details }),
      message,
      status,
    };
  }
}

/**
 * Middleware can read request data and add information to the context that will
 * be passed to the Action. If middleware throws an error, that error will fail
 * the request and the Action will not be invoked. Expected cases should return a
 * UserFacingError, which allows the request handler to know what data is safe to
 * return to end users.
 *
 * Middleware can provide validation in addition to parsing. For example, an auth
 * middleware can have policies for validating auth in addition to passing auth context
 * to the Action.
 */
export type AuthPolicy<T = any> = (
  request: Request<T>
) => Record<string, any> | Promise<Record<string, any>>;
