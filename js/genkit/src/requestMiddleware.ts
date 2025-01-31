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
export interface Request<T> {
  method: 'GET' | 'PUT' | 'POST' | 'DELETE' | 'OPTIONS' | 'QUERY';
  headers: Record<string, string>;
  body: T;
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
  constructor(
    public code: number,
    message: string
  ) {
    super(message);
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
export type Middleware<T> = (
  request: Request<T>
) => Record<string, any> | Promise<Record<string, any>>;
