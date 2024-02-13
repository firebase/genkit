/**
 * Interrupt error is an internal error thrown by flow states to interrupt execution of the step.
 */
export class InterruptError extends Error {}

/**
 * Extracts error message from the given error object, or if input is not an error then just turn the error into a string.
 */
export function getErrorMessage(e: any): string {
  if (e instanceof Error) {
    return e.message;
  }
  return `${e}`;
}

/**
 * Extracts stack trace from the given error object, or if input is not an error then returns undefined.
 */
export function getErrorStack(e: any): string | undefined {
  if (e instanceof Error) {
    return e.stack;
  }
  return undefined;
}

/**
 * Exception thrown when flow is not found in the flow state store.
 */
export class FlowNotFoundError extends Error {
  constructor(msg: string) {
    super(msg);
  }
}

/**
 * Exception thrown when flow execution is not completed yet.
 */
export class FlowStillRunningError extends Error {
  constructor(readonly flowId: string) {
    super(
      `flow ${flowId} is not done execution. Consider using waitForFlowToComplete to wait for ` +
      'completion before calling getOutput.'
    );
  }
}

/**
 * Exception thrown when flow execution resulted in an error.
 */
export class FlowExecutionError extends Error {
  constructor(
    readonly flowId: string,
    message: string,
    readonly originalMessage: string,
    readonly originalStacktrace?: any
  ) {
    super(message);
  }
}
