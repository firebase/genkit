import { Response } from 'express';
import { __RequestWithAuth, z, FlowAuthPolicy } from 'genkit';
import jwt from 'jsonwebtoken';
import jwksRsa from 'jwks-rsa';

interface Auth0User {
  sub: string;
  email?: string;
  email_verified?: boolean;
  [key: string]: any;
}

export function auth0Auth<I extends z.ZodTypeAny>(
  policy: ( user: Auth0User, input: z.infer<I>) => void | Promise<void>,
  config: { audience: string; issuerBaseURL: string }
): FlowAuthPolicy<I> {
  const jwksClient = jwksRsa({
    jwksUri: `${config.issuerBaseURL}/.well-known/jwks.json`,
  });

  const getSigningKey = (header: jwt.JwtHeader, callback: jwt.SigningKeyCallback) => {
    jwksClient.getSigningKey(header.kid, (err, key) => {
      const signingKey = key?.getPublicKey();
      callback(err, signingKey);
    });
  };

  return async (token: string | undefined, input: z.infer<I>) => {
    if (!token) {
      throw new Error('Authorization token is required');
    }

    try {
      // Verify and decode the token
      const user = await new Promise<Auth0User>((resolve, reject) => {
        jwt.verify(
          token,
          getSigningKey,
          {
            audience: config.audience,
            issuer: config.issuerBaseURL,
            algorithms: ['RS256'],
          },
          (err, decoded) => {
            if (err) reject(err);
            else resolve(decoded as Auth0User);
          }
        );
      });

      // Apply the custom policy with the user and input
      await policy(user, input);
    } catch (error) {
      throw new Error('Invalid or expired token');
    }
  };
}

function unauthorized(res: Response) {
  res.status(401);
  res.send('Unauthorized');
  res.end();
}
