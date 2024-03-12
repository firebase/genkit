import { Response } from 'express';
import { DecodedIdToken, getAuth } from 'firebase-admin/auth';
import { __RequestWithAuth, FlowAuthPolicy } from '@genkit-ai/flow';
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
    policy: policy as unknown as FlowAuthPolicy,
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
