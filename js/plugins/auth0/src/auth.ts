import { Response } from 'express';
import { auth } from 'express-oauth2-jwt-bearer';
import { __RequestWithAuth, z, FlowAuthPolicy } from 'genkit';
import * as express from 'express';

interface Auth0User {
  sub: string;
  email?: string;
  email_verified?: boolean;
  [key: string]: any;
}

export function auth0Auth<I extends z.ZodTypeAny>(
  policy: (user: Auth0User, input: z.infer<I>) => void | Promise<void>
): FlowAuthPolicy<I>;
export function auth0Auth<I extends z.ZodTypeAny>(
  policy: (user: Auth0User, input: z.infer<I>) => void | Promise<void>,
  config: { required: true; audience: string; issuerBaseURL: string }
): FlowAuthPolicy<I>;
export function auth0Auth<I extends z.ZodTypeAny>(
  policy: (user: Auth0User | undefined, input: z.infer<I>) => void | Promise<void>,
  config: { required: false; audience: string; issuerBaseURL: string }
): FlowAuthPolicy<I>;
export function auth0Auth<I extends z.ZodTypeAny>(
  policy: (user: Auth0User, input: z.infer<I>) => void | Promise<void>,
  config?: { required?: boolean; audience: string; issuerBaseURL: string }
): FlowAuthPolicy<I> {
  const required = config?.required ?? true;
  const checkJwt = auth({
    audience: config?.audience,
    issuerBaseURL: config?.issuerBaseURL,
  });

  return async (auth: Auth0User | undefined, input: z.infer<I>) => {
    if (required && !auth) {
      throw new Error('Auth is required');
    }
    return policy(auth as Auth0User, input);
  };
}

function unauthorized(res: Response) {
  res.status(401);
  res.send('Unauthorized');
  res.end();
}
