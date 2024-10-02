import { Response } from 'express';
import { auth } from 'express-oauth2-jwt-bearer';
import { __RequestWithAuth, z } from 'genkit';
import * as express from 'express';

interface Auth0User {
  sub: string;
  email?: string;
  email_verified?: boolean;
  [key: string]: any;
}

interface FlowAuth<I extends z.ZodTypeAny> {
  provider: express.RequestHandler;
  policy: (auth: unknown | undefined, input: z.infer<I>) => void | Promise<void>;
}

export function auth0Auth<I extends z.ZodTypeAny>(
  policy: (user: Auth0User, input: z.infer<I>) => void | Promise<void>
): FlowAuth<I>;
export function auth0Auth<I extends z.ZodTypeAny>(
  policy: (user: Auth0User, input: z.infer<I>) => void | Promise<void>,
  config: { required: true; audience: string; issuerBaseURL: string }
): FlowAuth<I>;
export function auth0Auth<I extends z.ZodTypeAny>(
  policy: (user: Auth0User | undefined, input: z.infer<I>) => void | Promise<void>,
  config: { required: false; audience: string; issuerBaseURL: string }
): FlowAuth<I>;
export function auth0Auth<I extends z.ZodTypeAny>(
  policy: (user: Auth0User, input: z.infer<I>) => void | Promise<void>,
  config?: { required?: boolean; audience: string; issuerBaseURL: string }
): FlowAuth<I> {
  const required = config?.required ?? true;
  const checkJwt = auth({
    audience: config?.audience,
    issuerBaseURL: config?.issuerBaseURL,
  });

  return {
    async policy(auth: unknown | undefined, input: z.infer<I>) {
      if (required && !auth) {
        throw new Error('Auth is required');
      }

      return policy(auth as Auth0User, input);
    },
    async provider(req, res, next) {
      checkJwt(req, res, (err) => {
        if (err) {
          if (required) {
            unauthorized(res);
          } else {
            next();
          }
          return;
        }

        (req as __RequestWithAuth).auth = req.auth;
        next();
      });
    },
  };
}

function unauthorized(res: Response) {
  res.status(401);
  res.send('Unauthorized');
  res.end();
}
