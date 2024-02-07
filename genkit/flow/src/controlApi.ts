import { Response } from 'express';
import { Request } from 'firebase-functions/v2/https';
import { TaskQueueFunction } from 'firebase-functions/v2/tasks';
import { FlowRunner } from './runner';
import { Operation } from '@google-genkit/common';
import { generateFlowId } from './utils';
import { FlowInvokeEnvelopeMessage } from './types';

const statusPathRegex = /^(\/.+)?\/invocations\/(.+)$/;
const startPathRegex = /^(\/.+)?\/invocations\/?$/;

export function createControlAPI(
  fr: FlowRunner<any, any>,
  tq: TaskQueueFunction<FlowInvokeEnvelopeMessage>
) {
  const interceptor = async (req: Request, res: Response) => {
    console.log('interceptor path: ', req.path);
    const statusMatch = req.path.match(statusPathRegex);
    if (req.method === 'GET' && statusMatch && statusMatch.length > 1) {
      const state = await fr.stateStore.load(
        statusMatch[statusMatch.length - 1]
      );
      if (!state) {
        res.status(404).send(`flow ${statusMatch[1]} not found`).end();
      }
      res.status(200).send(state?.operation).end();
      return;
    }
    if (req.method === 'PATCH' && statusMatch && statusMatch.length > 1) {
      const flowId = statusMatch[statusMatch.length - 1];
      if (req.query['async'] === 'false') {
        const state = await fr.run({
          flowId,
          resume: req.body.input,
        });
        res.status(200).send(state.operation).end();
        return;
      } else {
        await fr.dispatcher.dispatch(fr, {
          flowId,
          resume: req.body.input,
        });
        res.status(200).end();
        return;
      }
    }
    const startMatch = req.path.match(startPathRegex);
    if (req.method === 'POST' && startMatch) {
      const flowId = generateFlowId();
      if (req.query['async'] === 'false') {
        const state = await fr.run({
          flowId,
          input: req.body.input,
        });
        res.status(200).send(state.operation).end();
        return;
      } else {
        await fr.dispatcher.dispatch(fr, {
          flowId,
          input: req.body.input,
        });
        res
          .status(200)
          .send({
            done: false,
            name: flowId,
          } as Operation)
          .end();
        return;
      }
    }
    return await tq(req, res);
  };
  interceptor.__endpoint = tq.__endpoint;
  if (tq.hasOwnProperty('__requiredAPIs')) {
    interceptor.__requiredAPIs = tq['__requiredAPIs'];
  }
  return interceptor;
}
