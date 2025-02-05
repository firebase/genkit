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

import { describe, expect, it } from '@jest/globals';
import { Request } from 'genkit/authPolicy';
import {
  FirebaseContext,
  fakeToken,
  firebaseAuth,
  setDebugSkipTokenVerification,
} from '../src/auth';

function request(headers: Record<string, string> = {}): Request {
  return {
    method: 'POST',
    headers,
    body: undefined,
  };
}
describe('firebaseAuth', () => {
  setDebugSkipTokenVerification(true);

  describe('no policy', () => {
    it('handles noop', async () => {
      const context = await firebaseAuth()(request());
      expect(context).toEqual({});
    });

    it('handles all headers', async () => {
      const context = await firebaseAuth()(
        request({
          authorization: `bearer ${fakeToken({ sub: 'user' })}`,
          'x-firebase-appcheck': fakeToken({ sub: 'appId' }),
          'firebase-instance-id-token': 'token',
        })
      );
      expect(context).toEqual({
        auth: {
          uid: 'user',
          token: { sub: 'user' },
        },
        app: {
          appId: 'appId',
          token: { sub: 'appId' },
          alreadyConsumed: false,
        },
        instanceIdToken: 'token',
      });
    });
  });

  describe('declaritive policies', () => {
    it('handles signedIn', async () => {
      expect(() =>
        firebaseAuth({ signedIn: true })(request())
      ).rejects.toThrow();
      expect(await firebaseAuth({ signedIn: false })(request())).toEqual({});
      expect(
        await firebaseAuth({ signedIn: false })(
          request({ authorization: `bearer ${fakeToken({ sub: 'user' })}` })
        )
      ).toEqual({
        auth: {
          uid: 'user',
          token: {
            sub: 'user',
          },
        },
      });
    });

    it('handles emailVerified', async () => {
      expect(() =>
        firebaseAuth({ emailVerified: true })(request())
      ).rejects.toThrow();
      expect(await firebaseAuth({ emailVerified: false })(request())).toEqual(
        {}
      );
      expect(() =>
        firebaseAuth({ emailVerified: true })(
          request({ authorization: `bearer ${fakeToken({ sub: 'user' })}` })
        )
      ).rejects.toThrow();
      expect(() =>
        firebaseAuth({ emailVerified: true })(
          request({
            authorization: `bearer ${fakeToken({ sub: 'user', email: 'user@google.com', email_verified: 'false' })}`,
          })
        )
      ).rejects.toThrow();
      expect(
        await firebaseAuth({ emailVerified: true })(
          request({
            authorization: `bearer ${fakeToken({ sub: 'user', email: 'user@google.com', email_verified: 'true' })}`,
          })
        )
      ).toEqual({
        auth: {
          uid: 'user',
          token: {
            sub: 'user',
            email: 'user@google.com',
            email_verified: 'true',
          },
        },
      });
    });

    it('enforces hasClaim (string)', async () => {
      expect(
        await firebaseAuth({ hasClaim: 'email' })(
          request({
            authorization: `bearer ${fakeToken({ sub: 'user', email: 'user@google.com' })}`,
          })
        )
      ).toEqual({
        auth: {
          uid: 'user',
          token: {
            sub: 'user',
            email: 'user@google.com',
          },
        },
      });
      expect(() =>
        firebaseAuth({ hasClaim: 'admin' })(
          request({
            authorization: `bearer ${fakeToken({
              sub: 'user',
            })}`,
          })
        )
      ).rejects.toThrow();
      expect(() =>
        firebaseAuth({ hasClaim: 'admin' })(
          request({
            authorization: `bearer ${fakeToken({
              sub: 'user',
              admin: 'false',
            })}`,
          })
        )
      ).rejects.toThrow();
    });

    it('handles hasClaim(string[])', async () => {
      expect(() =>
        firebaseAuth({ hasClaim: ['email', 'admin'] })(
          request({
            authorization: `bearer ${fakeToken({
              sub: 'user',
              admin: 'true',
            })}`,
          })
        )
      ).rejects.toThrow();
      expect(() =>
        firebaseAuth({ hasClaim: ['email', 'admin'] })(
          request({
            authorization: `bearer ${fakeToken({
              sub: 'user',
              admin: 'false',
              email: 'user@google.com',
            })}`,
          })
        )
      ).rejects.toThrow();
      expect(
        await firebaseAuth({ hasClaim: ['email', 'admin'] })(
          request({
            authorization: `bearer ${fakeToken({
              sub: 'user',
              admin: 'true',
              email: 'user@google.com',
            })}`,
          })
        )
      ).toEqual({
        auth: {
          uid: 'user',
          token: {
            sub: 'user',
            admin: 'true',
            email: 'user@google.com',
          },
        },
      });
    });

    it('handles hasClaim(Record<string, boolean>)', async () => {
      expect(() =>
        firebaseAuth({
          hasClaim: {
            admin: 'true',
            humor: 'dad',
          },
        })(
          request({
            authorization: `bearer ${fakeToken({
              uid: 'user',
              admin: 'true',
            })}`,
          })
        )
      ).rejects.toThrow();
      expect(() =>
        firebaseAuth({
          hasClaim: {
            admin: 'true',
            humor: 'dad',
          },
        })(
          request({
            authorization: `bearer ${fakeToken({
              uid: 'user',
              admin: 'true',
              humor: 'programming',
            })}`,
          })
        )
      ).rejects.toThrow();
      expect(
        await firebaseAuth({
          hasClaim: {
            admin: 'true',
            humor: 'dad',
          },
        })(
          request({
            authorization: `bearer ${fakeToken({
              sub: 'user',
              admin: 'true',
              humor: 'dad',
            })}`,
          })
        )
      ).toEqual({
        auth: {
          uid: 'user',
          token: {
            sub: 'user',
            admin: 'true',
            humor: 'dad',
          },
        },
      });
    });

    it('handles enforceAppCheck', async () => {
      expect(
        await firebaseAuth({ enforceAppCheck: true })(
          request({
            'x-firebase-appcheck': fakeToken({ sub: 'appId' }),
          })
        )
      ).toEqual({
        app: {
          appId: 'appId',
          token: {
            sub: 'appId',
          },
          alreadyConsumed: false,
        },
      });
      expect(() =>
        firebaseAuth({ enforceAppCheck: true })(request())
      ).rejects.toThrow();
    });
  });

  describe('policy functions', () => {
    it('passes context', () => {
      firebaseAuth((context: FirebaseContext) => {
        expect(context).toEqual({
          auth: {
            uid: 'user',
            token: {
              sub: 'user',
            },
          },
          app: {
            appId: 'app',
            token: {
              sub: 'app',
            },
            alreadyConsumed: false,
          },
          instanceIdToken: 'iid',
        });
      })(
        request({
          authorization: `bearer ${fakeToken({ sub: 'user' })}`,
          'x-firebase-appcheck': fakeToken({ sub: 'app' }),
          'firebase-instance-id-token': 'iid',
        })
      );
      firebaseAuth((context: FirebaseContext) => {
        expect(context).toEqual({});
      })(request());
    });
  });
});
