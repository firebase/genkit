import { FlowState } from '../types/flow';
import { SpanData } from '../types/trace';

export interface StateRetriever {
  listFlowRuns(): Promise<FlowState[]>;
  getFlowRun(flowId: string): Promise<FlowState | null>;
  getTrace(traceId: string): Promise<SpanData | null>;
}
