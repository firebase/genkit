// TODO(sam-gc): Actually have proper types here...

export interface StateRetriever {
  listFlowRuns(): Promise<Array<unknown>>;
  getFlowRun(flowId: string): Promise<unknown>;
  getTrace(traceId: string): Promise<unknown>;
}
