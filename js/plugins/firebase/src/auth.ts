import { Response } from 'express';
import { DecodedIdToken, getAuth } from 'firebase-admin/auth';
import { __RequestWithAuth } from '@genkit-ai/flow';
import { FunctionFlowAuth } from './functions';

export function firebaseAuth(
  policy: (user: DecodedIdToken) => void | Promise<void>
): FunctionFlowAuth;
export function firebaseAuth(
  policy: (user: DecodedIdToken) => void | Promise<void>,
  config: { required: true }
): FunctionFlowAuth;
export function firebaseAuth(
  policy: (user?: DecodedIdToken) => void | Promise<void>,
  config: { required: false }
): FunctionFlowAuth;
export function firebaseAuth(
  policy: (user: DecodedIdToken) => void | Promise<void>,
  config?: { required: boolean }
): FunctionFlowAuth {
  const required = config?.required || true;
  return {
    async policy(auth?: unknown) {
      // If required is true, then auth will always be set when called from
      // an HTTP context. However, we need to wrap the user-provided policy
      // to check for presence of auth when the flow is executed from runFlow
      // or an action context.
      if (required && !auth) {
        throw new Error('Auth is required');
      }

      return policy(auth as DecodedIdToken);
    },
    async provider(req, res, next) {
      const token = req.headers['authorization']?.split(/[Bb]earer /)[1];
      let decoded: DecodedIdToken;

      if (!token) {
        if (required) {
          unauthorized(res);
        } else {
          next();
        }
        return;
      }
      try {
        decoded = await getAuth().verifyIdToken(token);
      } catch (e) {
        unauthorized(res);
        return;
      }

      (req as __RequestWithAuth).auth = decoded;

      next();
    },
  };
}

function unauthorized(res: Response) {
  res.status(403);
  res.send('Unauthorized');
  res.end();
}
