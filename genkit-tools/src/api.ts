/**
 * Shared API definitions for headless CLI and emulator servers.
 * This is the only file that the UI should reference outside of its own
 * submodule.
 */

export const enum CliEndpoints {
  EXAMPLE = 'example:echo',
}

export interface CliApi {
  Example: {
    RequestQuery: {
      echo: string;
    };
    Response: {
      echoResponse: string;
    };
  };
}
