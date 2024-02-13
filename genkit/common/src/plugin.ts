import { FlowStateStore } from './flowTypes';
import { TraceStore } from './tracing';
import { Action } from './types';

export interface Provider<T> {
  id: string;
  value: T;
}

export interface Plugin {
  name: string;
  provides: {
    models?: Action<any, any, any>[];
    retrievers?: Action<any, any, any>[];
    embedders?: Action<any, any, any>[];
    indexers?: Action<any, any, any>[];
    flowStateStore?: Provider<FlowStateStore>;
    traceStore?: Provider<TraceStore>;
  };
}
