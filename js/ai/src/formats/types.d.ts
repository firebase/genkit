import { GenerateResponse, GenerateResponseChunk } from '../generate';
import { GenerateRequest } from '../model';

export interface Formatter {
  (req: GenerateRequest): {
    parseChunk?: (
      chunk: GenerateResponseChunk,
      emit: (chunk: any) => void
    ) => void;
    parseResponse(response: GenerateResponse): any;
    instructions?: boolean | string;
  };
}
