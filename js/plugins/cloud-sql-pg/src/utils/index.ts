import { GoogleAuth } from "google-auth-library";

/**
 * Get email address associated with current authenticated IAM principal.
 * Email will be used for automatic IAM database authentication to Cloud SQL.
 *
 * @param {GoogleAuth} auth - object to use in finding the associated IAM principal email address.
 * @returns {string} email - email address associated with the current authenticated IAM principal
 */
export const getIAMPrincipalEmail = async (auth: GoogleAuth): Promise<string> => {
  const credentials = await auth.getCredentials();

  if ('client_email' in credentials && credentials.client_email !== undefined) {
    return credentials.client_email.replace(".gserviceaccount.com", "");
  }

  const accessToken = await auth.getAccessToken();
  const client = await auth.getClient()

  const url = `https://oauth2.googleapis.com/tokeninfo?access_token=${accessToken}`;
  const clientResponse = await client.request({url}).then((res: { data: any; }) => res.data)

  if (!('email' in clientResponse)) {
    throw new Error(
      "Failed to automatically obtain authenticated IAM principal's " +
      "email address using environment's ADC credentials!"
    )
  }
  const email = clientResponse['email']
  return email.replace(".gserviceaccount.com", "");
}
