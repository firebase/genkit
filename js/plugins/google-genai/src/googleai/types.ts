/**
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/**
 * Params passed to getGenerativeModel() or GoogleAIFileManager().
 * @public
 */
export interface RequestOptions {
  /**
   * Request timeout in milliseconds.
   */
  timeout?: number;
  /**
   * Version of API endpoint to call (e.g. "v1" or "v1beta"). If not specified,
   * defaults to latest stable version.
   */
  apiVersion?: string;
  /**
   * Additional attribution information to include in the x-goog-api-client header.
   * Used by wrapper SDKs.
   */
  apiClient?: string;
  /**
   * Base endpoint url. Defaults to "https://generativelanguage.googleapis.com"
   */
  baseUrl?: string;
  /**
   * Custom HTTP request headers.
   */
  customHeaders?: Headers | Record<string, string>;
}

/**
 * Individual response from generateContent and generateContentStream.
 * `generateContentStream()` will return one in each chunk until
 * the stream is done.
 * @public
 */
export interface GenerateContentResponse {
  /** Candidate responses from the model. */
  candidates?: GenerateContentCandidate[];
  /** The prompt's feedback related to the content filters. */
  promptFeedback?: PromptFeedback;
  /** Metadata on the generation request's token usage. */
  usageMetadata?: UsageMetadata;
}

/**
 * Metadata on the generation request's token usage.
 * @public
 */
export interface UsageMetadata {
  /** Number of tokens in the prompt. */
  promptTokenCount: number;
  /** Total number of tokens across the generated candidates. */
  candidatesTokenCount: number;
  /** Total token count for the generation request (prompt + candidates). */
  totalTokenCount: number;
  /** Total token count in the cached part of the prompt, i.e. in the cached content. */
  cachedContentTokenCount?: number;
}

/**
 * If the prompt was blocked, this will be populated with `blockReason` and
 * the relevant `safetyRatings`.
 * @public
 */
export interface PromptFeedback {
  blockReason: BlockReason;
  safetyRatings: SafetyRating[];
  blockReasonMessage?: string;
}

/**
 * Reason that a prompt was blocked.
 * @public
 */
export enum BlockReason {
  // A blocked reason was not specified.
  BLOCKED_REASON_UNSPECIFIED = 'BLOCKED_REASON_UNSPECIFIED',
  // Content was blocked by safety settings.
  SAFETY = 'SAFETY',
  // Content was blocked, but the reason is uncategorized.
  OTHER = 'OTHER',
}

/**
 * A safety rating associated with a GenerateContentCandidate
 * @public
 */
export interface SafetyRating {
  category: HarmCategory;
  probability: HarmProbability;
}

/**
 * Probability that a prompt or candidate matches a harm category.
 * @public
 */
export enum HarmProbability {
  /** Probability is unspecified. */
  HARM_PROBABILITY_UNSPECIFIED = 'HARM_PROBABILITY_UNSPECIFIED',
  /** Content has a negligible chance of being unsafe. */
  NEGLIGIBLE = 'NEGLIGIBLE',
  /** Content has a low chance of being unsafe. */
  LOW = 'LOW',
  /** Content has a medium chance of being unsafe. */
  MEDIUM = 'MEDIUM',
  /** Content has a high chance of being unsafe. */
  HIGH = 'HIGH',
}

/**
 * A candidate returned as part of a GenerateContentResponse.
 * @public
 */
export interface GenerateContentCandidate {
  index: number;
  content: Content;
  finishReason?: FinishReason;
  finishMessage?: string;
  safetyRatings?: SafetyRating[];
  citationMetadata?: CitationMetadata;
  /** Average log probability score of the candidate. */
  avgLogprobs?: number;
  /** Log-likelihood scores for the response tokens and top tokens. */
  logprobsResult?: LogprobsResult;
  /** Search grounding metadata. */
  groundingMetadata?: GroundingMetadata;
}
/**
 * Citation metadata that may be found on a GenerateContentCandidate.
 * @public
 */
export interface CitationMetadata {
  citationSources: CitationSource[];
}

/**
 * Logprobs Result
 * @public
 */
export interface LogprobsResult {
  /** Length = total number of decoding steps. */
  topCandidates: TopCandidates[];
  /**
   * Length = total number of decoding steps.
   * The chosen candidates may or may not be in topCandidates.
   */
  chosenCandidates: LogprobsCandidate[];
}

/**
 * Candidate for the logprobs token and score.
 * @public
 */
export interface LogprobsCandidate {
  /** The candidate's token string value. */
  token: string;
  /** The candidate's token id value. */
  tokenID: number;
  /** The candidate's log probability. */
  logProbability: number;
}

/**
 * Candidates with top log probabilities at each decoding step
 */
export interface TopCandidates {
  /** Sorted by log probability in descending order. */
  candidates: LogprobsCandidate[];
}

/**
 * A single citation source.
 * @public
 */
export interface CitationSource {
  startIndex?: number;
  endIndex?: number;
  uri?: string;
  license?: string;
}

/**
 * Reason that a candidate finished.
 * @public
 */
export enum FinishReason {
  // Default value. This value is unused.
  FINISH_REASON_UNSPECIFIED = 'FINISH_REASON_UNSPECIFIED',
  // Natural stop point of the model or provided stop sequence.
  STOP = 'STOP',
  // The maximum number of tokens as specified in the request was reached.
  MAX_TOKENS = 'MAX_TOKENS',
  // The candidate content was flagged for safety reasons.
  SAFETY = 'SAFETY',
  // The candidate content was flagged for recitation reasons.
  RECITATION = 'RECITATION',
  // The candidate content was flagged for using an unsupported language.
  LANGUAGE = 'LANGUAGE',
  // Token generation stopped because the content contains forbidden terms.
  BLOCKLIST = 'BLOCKLIST',
  // Token generation stopped for potentially containing prohibited content.
  PROHIBITED_CONTENT = 'PROHIBITED_CONTENT',
  // Token generation stopped because the content potentially contains Sensitive Personally Identifiable Information (SPII).
  SPII = 'SPII',
  // The function call generated by the model is invalid.
  MALFORMED_FUNCTION_CALL = 'MALFORMED_FUNCTION_CALL',
  // Unknown reason.
  OTHER = 'OTHER',
}

/**
 * Response object wrapped with helper methods.
 *
 * @public
 */
export interface EnhancedGenerateContentResponse
  extends GenerateContentResponse {
  /**
   * Returns the text string assembled from all `Part`s of the first candidate
   * of the response, if available.
   * Throws if the prompt or candidate was blocked.
   */
  text: () => string;

  /**
   * Returns function calls found in any `Part`s of the first candidate
   * of the response, if available.
   * Throws if the prompt or candidate was blocked.
   */
  functionCalls: () => FunctionCall[] | undefined;
}

/**
 * Request sent to `generateContent` endpoint.
 * @public
 */
export interface GenerateContentRequest extends BaseParams {
  contents: Content[];
  tools?: Tool[];
  toolConfig?: ToolConfig;
  systemInstruction?: string | Part | Content;
  /**
   * This is the name of a `CachedContent` and not the cache object itself.
   */
  cachedContent?: string;
}

/**
 * Content type for both prompts and response candidates.
 * @public
 */
export interface Content {
  role: string;
  parts: Part[];
}

/**
 * Content part - includes text or image part types.
 * @public
 */
export type Part =
  | TextPart
  | InlineDataPart
  | FunctionCallPart
  | FunctionResponsePart
  | FileDataPart
  | ExecutableCodePart
  | CodeExecutionResultPart;

/**
 * Content part interface if the part represents a text string.
 * @public
 */
export interface TextPart {
  text: string;
  inlineData?: never;
  functionCall?: never;
  functionResponse?: never;
  fileData?: never;
  executableCode?: never;
  codeExecutionResult?: never;
}

/**
 * Content part interface if the part represents an image.
 * @public
 */
export interface InlineDataPart {
  text?: never;
  inlineData: GenerativeContentBlob;
  functionCall?: never;
  functionResponse?: never;
  fileData?: never;
  executableCode?: never;
  codeExecutionResult?: never;
}

/**
 * Interface for sending an image.
 * @public
 */
export interface GenerativeContentBlob {
  mimeType: string;
  /**
   * Image as a base64 string.
   */
  data: string;
}

/**
 * Content part interface if the part represents a FunctionCall.
 * @public
 */
export interface FunctionCallPart {
  text?: never;
  inlineData?: never;
  functionCall: FunctionCall;
  functionResponse?: never;
  fileData?: never;
  executableCode?: never;
  codeExecutionResult?: never;
}

/**
 * A predicted [FunctionCall] returned from the model
 * that contains a string representing the [FunctionDeclaration.name]
 * and a structured JSON object containing the parameters and their values.
 * @public
 */
export interface FunctionCall {
  name: string;
  args: object;
}

/**
 * @public
 */
export enum FunctionCallingMode {
  // Unspecified function calling mode. This value should not be used.
  MODE_UNSPECIFIED = 'MODE_UNSPECIFIED',
  // Default model behavior, model decides to predict either a function call
  // or a natural language repspose.
  AUTO = 'AUTO',
  // Model is constrained to always predicting a function call only.
  // If "allowed_function_names" are set, the predicted function call will be
  // limited to any one of "allowed_function_names", else the predicted
  // function call will be any one of the provided "function_declarations".
  ANY = 'ANY',
  // Model will not predict any function call. Model behavior is same as when
  // not passing any function declarations.
  NONE = 'NONE',
}

/**
 * Content part interface if the part represents FunctionResponse.
 * @public
 */
export interface FunctionResponsePart {
  text?: never;
  inlineData?: never;
  functionCall?: never;
  functionResponse: FunctionResponse;
  fileData?: never;
  executableCode?: never;
  codeExecutionResult?: never;
}

/**
 * The result output from a [FunctionCall] that contains a string
 * representing the [FunctionDeclaration.name]
 * and a structured JSON object containing any output
 * from the function is used as context to the model.
 * This should contain the result of a [FunctionCall]
 * made based on model prediction.
 * @public
 */
export interface FunctionResponse {
  name: string;
  response: object;
}

/**
 * Content part interface if the part represents FileData.
 * @public
 */
export interface FileDataPart {
  text?: never;
  inlineData?: never;
  functionCall?: never;
  functionResponse?: never;
  fileData: FileData;
  executableCode?: never;
  codeExecutionResult?: never;
}

/**
 * Data pointing to a file uploaded with the Files API.
 * @public
 */
export interface FileData {
  mimeType: string;
  fileUri: string;
}

/**
 * Content part containing executable code generated by the model.
 * @public
 */
export interface ExecutableCodePart {
  text?: never;
  inlineData?: never;
  functionCall?: never;
  functionResponse?: never;
  fileData?: never;
  executableCode: ExecutableCode;
  codeExecutionResult?: never;
}

/**
 * Code generated by the model that is meant to be executed, where the result
 * is returned to the model.
 * Only generated when using the code execution tool, in which the code will
 * be automatically executed, and a corresponding `CodeExecutionResult` will
 * also be generated.
 *
 * @public
 */
export interface ExecutableCode {
  /**
   * Programming language of the `code`.
   */
  language: ExecutableCodeLanguage;
  /**
   * The code to be executed.
   */
  code: string;
}

/**
 * @public
 */
export enum ExecutableCodeLanguage {
  LANGUAGE_UNSPECIFIED = 'language_unspecified',
  PYTHON = 'python',
}

/**
 * Content part containing the result of executed code.
 * @public
 */
export interface CodeExecutionResultPart {
  text?: never;
  inlineData?: never;
  functionCall?: never;
  functionResponse?: never;
  fileData?: never;
  executableCode?: never;
  codeExecutionResult: CodeExecutionResult;
}

/**
 * Result of executing the `ExecutableCode`.
 * Only generated when using code execution, and always follows a `Part`
 * containing the `ExecutableCode`.
 * @public
 */
export interface CodeExecutionResult {
  /**
   * Outcome of the code execution.
   */
  outcome: Outcome;
  /**
   * Contains stdout when code execution is successful, stderr or other
   * description otherwise.
   */
  output: string;
}

/**
 * Possible outcomes of code execution.
 * @public
 */
export enum Outcome {
  /**
   * Unspecified status. This value should not be used.
   */
  OUTCOME_UNSPECIFIED = 'outcome_unspecified',
  /**
   * Code execution completed successfully.
   */
  OUTCOME_OK = 'outcome_ok',
  /**
   * Code execution finished but with a failure. `stderr` should contain the
   * reason.
   */
  OUTCOME_FAILED = 'outcome_failed',
  /**
   * Code execution ran for too long, and was cancelled. There may or may not
   * be a partial output present.
   */
  OUTCOME_DEADLINE_EXCEEDED = 'outcome_deadline_exceeded',
}

/**
 * Structured representation of a function declaration as defined by the
 * [OpenAPI 3.0 specification](https://spec.openapis.org/oas/v3.0.3). Included
 * in this declaration are the function name and parameters. This
 * FunctionDeclaration is a representation of a block of code that can be used
 * as a Tool by the model and executed by the client.
 * @public
 */
export declare interface FunctionDeclaration {
  /**
   * The name of the function to call. Must start with a letter or an
   * underscore. Must be a-z, A-Z, 0-9, or contain underscores and dashes, with
   * a max length of 64.
   */
  name: string;
  /**
   * Optional. Description and purpose of the function. Model uses it to decide
   * how and whether to call the function.
   */
  description?: string;
  /**
   * Optional. Describes the parameters to this function in JSON Schema Object
   * format. Reflects the Open API 3.03 Parameter Object. string Key: the name
   * of the parameter. Parameter names are case sensitive. Schema Value: the
   * Schema defining the type used for the parameter. For function with no
   * parameters, this can be left unset.
   *
   * @example with 1 required and 1 optional parameter: type: OBJECT properties:
   * ```
   * param1:
   *
   *   type: STRING
   * param2:
   *
   *  type: INTEGER
   * required:
   *
   *   - param1
   * ```
   */
  parameters?: FunctionDeclarationSchema;
}

/**
 * Schema for parameters passed to {@link FunctionDeclaration.parameters}.
 * @public
 */
export interface FunctionDeclarationSchema {
  /** The type of the parameter. */
  type: SchemaType;
  /** The format of the parameter. */
  properties: { [k: string]: FunctionDeclarationSchemaProperty };
  /** Optional. Description of the parameter. */
  description?: string;
  /** Optional. Array of required parameters. */
  required?: string[];
}

/**
 * Contains the list of OpenAPI data types
 * as defined by https://swagger.io/docs/specification/data-models/data-types/
 * @public
 */
export enum SchemaType {
  /** String type. */
  STRING = 'string',
  /** Number type. */
  NUMBER = 'number',
  /** Integer type. */
  INTEGER = 'integer',
  /** Boolean type. */
  BOOLEAN = 'boolean',
  /** Array type. */
  ARRAY = 'array',
  /** Object type. */
  OBJECT = 'object',
}

/**
 * Schema for top-level function declaration
 * @public
 */
export type FunctionDeclarationSchemaProperty = Schema;

/**
 * Schema is used to define the format of input/output data.
 * Represents a select subset of an OpenAPI 3.0 schema object.
 * More fields may be added in the future as needed.
 * @public
 */
export type Schema =
  | StringSchema
  | NumberSchema
  | IntegerSchema
  | BooleanSchema
  | ArraySchema
  | ObjectSchema;

export interface BaseSchema {
  /** Optional. Description of the value. */
  description?: string;
  /** If true, the value can be null. */
  nullable?: boolean;

  // The field 'example' is accepted, but in testing, it seems like it accepts
  // any value of any type, even when that doesn't match the type that the
  // schema describes, and it doesn't appear to affect the model's output.
}

/**
 * Describes a JSON-encodable floating point number.
 *
 * @public
 */
export interface NumberSchema extends BaseSchema {
  type: typeof SchemaType.NUMBER;
  /** Optional. The format of the number. */
  format?: 'float' | 'double';

  // Note that the API accepts `minimum` and `maximum` fields here, as numbers,
  // but when tested they had no effect.
}

/**
 * Describes a JSON-encodable integer.
 *
 * @public
 */
export interface IntegerSchema extends BaseSchema {
  type: typeof SchemaType.INTEGER;
  /** Optional. The format of the number. */
  format?: 'int32' | 'int64'; // server rejects int32 or int64

  // Note that the API accepts minimum and maximum fields here, as numbers,
  // but when tested they had no effect.
}

/**
 * Describes a string.
 *
 * @public
 */
export type StringSchema = SimpleStringSchema | EnumStringSchema;

/**
 * Describes a simple string schema, with or without format
 *
 * @public
 */
export interface SimpleStringSchema extends BaseSchema {
  type: typeof SchemaType.STRING;

  // Note: These undefined values are needed to help the type system, they won't,
  // be passed to the API as they are undefined
  format?: 'date-time' | undefined;

  enum?: never;
}

/**
 * Describes a string enum
 *
 * @public
 */
export interface EnumStringSchema extends BaseSchema {
  type: typeof SchemaType.STRING;

  format: 'enum';

  /** Possible values for this enum */
  enum: string[];
}

/**
 * Describes a boolean, either 'true' or 'false'.
 *
 * @public
 */
export interface BooleanSchema extends BaseSchema {
  type: typeof SchemaType.BOOLEAN;
}

/**
 * Describes an array, an ordered list of values.
 *
 * @public
 */
export interface ArraySchema extends BaseSchema {
  type: typeof SchemaType.ARRAY;
  /** A schema describing the entries in the array. */
  items: Schema;

  /** The minimum number of items in the array. */
  minItems?: number;
  /** The maximum number of items in the array. */
  maxItems?: number;
}

/**
 * Describes a JSON object, a mapping of specific keys to values.
 *
 * @public
 */
export interface ObjectSchema extends BaseSchema {
  type: typeof SchemaType.OBJECT;
  /** Describes the properties of the JSON object. Must not be empty. */
  properties: { [k: string]: Schema };
  /**
   * A list of keys declared in the properties object.
   * Required properties will always be present in the generated object.
   */
  required?: string[];

  // Note that the API accepts the `minProperties`, and `maxProperties` fields,
  // but they may only be advisory.
}

/**
 * Schema for parameters passed to {@link FunctionDeclaration.parameters}.
 * @public
 */
export interface FunctionDeclarationSchema {
  /** The type of the parameter. */
  type: SchemaType;
  /** The format of the parameter. */
  properties: { [k: string]: FunctionDeclarationSchemaProperty };
  /** Optional. Description of the parameter. */
  description?: string;
  /** Optional. Array of required parameters. */
  required?: string[];
}

/**
 * Base parameters for a number of methods.
 * @public
 */
export interface BaseParams {
  safetySettings?: SafetySetting[];
  generationConfig?: GenerationConfig;
}

/**
 * Safety setting that can be sent as part of request parameters.
 * @public
 */
export interface SafetySetting {
  category: HarmCategory;
  threshold: HarmBlockThreshold;
}

/**
 * Harm categories that would cause prompts or candidates to be blocked.
 * @public
 */
export enum HarmCategory {
  HARM_CATEGORY_UNSPECIFIED = 'HARM_CATEGORY_UNSPECIFIED',
  HARM_CATEGORY_HATE_SPEECH = 'HARM_CATEGORY_HATE_SPEECH',
  HARM_CATEGORY_SEXUALLY_EXPLICIT = 'HARM_CATEGORY_SEXUALLY_EXPLICIT',
  HARM_CATEGORY_HARASSMENT = 'HARM_CATEGORY_HARASSMENT',
  HARM_CATEGORY_DANGEROUS_CONTENT = 'HARM_CATEGORY_DANGEROUS_CONTENT',
  HARM_CATEGORY_CIVIC_INTEGRITY = 'HARM_CATEGORY_CIVIC_INTEGRITY',
}

/**
 * Threshold above which a prompt or candidate will be blocked.
 * @public
 */
export enum HarmBlockThreshold {
  /** Threshold is unspecified. */
  HARM_BLOCK_THRESHOLD_UNSPECIFIED = 'HARM_BLOCK_THRESHOLD_UNSPECIFIED',
  /** Content with NEGLIGIBLE will be allowed. */
  BLOCK_LOW_AND_ABOVE = 'BLOCK_LOW_AND_ABOVE',
  /** Content with NEGLIGIBLE and LOW will be allowed. */
  BLOCK_MEDIUM_AND_ABOVE = 'BLOCK_MEDIUM_AND_ABOVE',
  /** Content with NEGLIGIBLE, LOW, and MEDIUM will be allowed. */
  BLOCK_ONLY_HIGH = 'BLOCK_ONLY_HIGH',
  /** All content will be allowed. */
  BLOCK_NONE = 'BLOCK_NONE',
}

/**
 * Config options for content-related requests
 * @public
 */
export interface GenerationConfig {
  candidateCount?: number;
  stopSequences?: string[];
  maxOutputTokens?: number;
  temperature?: number;
  topP?: number;
  topK?: number;
  /**
   * Output response mimetype of the generated candidate text.
   * Supported mimetype:
   *   `text/plain`: (default) Text output.
   *   `application/json`: JSON response in the candidates.
   */
  responseMimeType?: string;
  /**
   * Output response schema of the generated candidate text.
   * Note: This only applies when the specified `responseMIMEType` supports a schema; currently
   * this is limited to `application/json`.
   */
  responseSchema?: ResponseSchema;
  /**
   * Presence penalty applied to the next token's logprobs if the token has
   * already been seen in the response.
   */
  presencePenalty?: number;
  /**
   * Frequency penalty applied to the next token's logprobs, multiplied by the
   * number of times each token has been seen in the respponse so far.
   */
  frequencyPenalty?: number;
  /**
   * If True, export the logprobs results in response.
   */
  responseLogprobs?: boolean;
  /**
   * Valid if responseLogProbs is set to True. This will set the number of top
   * logprobs to return at each decoding step in the logprobsResult.
   */
  logprobs?: number;
}

/**
 * Schema passed to `GenerationConfig.responseSchema`
 * @public
 */
export type ResponseSchema = Schema;

/**
 * Tool config. This config is shared for all tools provided in the request.
 * @public
 */
export interface ToolConfig {
  functionCallingConfig: FunctionCallingConfig;
}

/**
 * @public
 */
export interface FunctionCallingConfig {
  mode?: FunctionCallingMode;
  allowedFunctionNames?: string[];
}

/**
 * Defines a tool that model can call to access external knowledge.
 * @public
 */
export declare type Tool =
  | FunctionDeclarationsTool
  | CodeExecutionTool
  | GoogleSearchRetrievalTool;

/**
 * A FunctionDeclarationsTool is a piece of code that enables the system to
 * interact with external systems to perform an action, or set of actions,
 * outside of knowledge and scope of the model.
 * @public
 */
export declare interface FunctionDeclarationsTool {
  /**
   * Optional. One or more function declarations
   * to be passed to the model along with the current user query. Model may
   * decide to call a subset of these functions by populating
   * [FunctionCall][content.part.functionCall] in the response. User should
   * provide a [FunctionResponse][content.part.functionResponse] for each
   * function call in the next turn. Based on the function responses, Model will
   * generate the final response back to the user. Maximum 64 function
   * declarations can be provided.
   */
  functionDeclarations?: FunctionDeclaration[];
}

/**
 * Enables the model to execute code as part of generation.
 * @public
 */
export interface CodeExecutionTool {
  /**
   * Provide an empty object to enable code execution. This field may have
   * subfields added in the future.
   */
  codeExecution: {};
}

/**
 * Retrieval tool that is powered by Google search.
 * @public
 */
export declare interface GoogleSearchRetrievalTool {
  /**
   * Google search retrieval tool config.
   */
  googleSearchRetrieval?: GoogleSearchRetrieval;
}

/**
 * Retrieval tool that is powered by Google search.
 * @public
 */
export declare interface GoogleSearchRetrieval {
  /**
   * Specifies the dynamic retrieval configuration for the given source.
   */
  dynamicRetrievalConfig?: DynamicRetrievalConfig;
}

/**
 * Specifies the dynamic retrieval configuration for the given source.
 * @public
 */
export declare interface DynamicRetrievalConfig {
  /**
   * The mode of the predictor to be used in dynamic retrieval.
   */
  mode?: DynamicRetrievalMode;
  /**
   * The threshold to be used in dynamic retrieval. If not set, a system default
   * value is used.
   */
  dynamicThreshold?: number;
}

/**
 * The mode of the predictor to be used in dynamic retrieval.
 * @public
 */
export enum DynamicRetrievalMode {
  // Unspecified function calling mode. This value should not be used.
  MODE_UNSPECIFIED = 'MODE_UNSPECIFIED',
  // Run retrieval only when system decides it is necessary.
  MODE_DYNAMIC = 'MODE_DYNAMIC',
}

/**
 * Metadata returned to client when grounding is enabled.
 * @public
 */
export declare interface GroundingMetadata {
  /**
   * Google search entry for the following-up web searches.
   */
  searchEntryPoint?: SearchEntryPoint;
  /**
   * List of supporting references retrieved from specified grounding source.
   */
  groundingChunks?: GroundingChunk[];
  /**
   * List of grounding support.
   */
  groundingSupports?: GroundingSupport[];
  /**
   * Metadata related to retrieval in the grounding flow.
   */
  retrievalMetadata?: RetrievalMetadata;
  /**
   * * Web search queries for the following-up web search.
   */
  webSearchQueries: string[];
}

/**
 * Google search entry point.
 * @public
 */
export declare interface SearchEntryPoint {
  /**
   * Web content snippet that can be embedded in a web page or an app webview.
   */
  renderedContent?: string;
  /**
   * Base64 encoded JSON representing array of <search term, search url> tuple.
   */
  sdkBlob?: string;
}

/**
 * Grounding chunk.
 * @public
 */
export declare interface GroundingChunk {
  /**
   *  Chunk from the web.
   */
  web?: GroundingChunkWeb;
}

/**
 * Chunk from the web.
 * @public
 */
export declare interface GroundingChunkWeb {
  /**
   * URI reference of the chunk.
   */
  uri?: string;
  /**
   * Title of the chunk.
   */
  title?: string;
}

/**
 * Grounding support.
 * @public
 */
export declare interface GroundingSupport {
  /**
   * URI reference of the chunk.
   */
  segment?: string;
  /**
   * A list of indices (into 'grounding_chunk') specifying the citations
   * associated with the claim. For instance [1,3,4] means that
   * grounding_chunk[1], grounding_chunk[3], grounding_chunk[4] are the
   * retrieved content attributed to the claim.
   */
  groundingChunckIndices?: number[];
  /**
   * Confidence score of the support references. Ranges from 0 to 1. 1 is the
   * most confident. This list must have the same size as the
   * grounding_chunk_indices.
   */
  confidenceScores?: number[];
}

/**
 * Metadata related to retrieval in the grounding flow.
 * @public
 */
export declare interface RetrievalMetadata {
  /**
   * Score indicating how likely information from google search could help
   * answer the prompt. The score is in the range [0, 1], where 0 is the least
   * likely and 1 is the most likely. This score is only populated when google
   * search grounding and dynamic retrieval is enabled. It will becompared to
   * the threshold to determine whether to trigger google search.
   */
  googleSearchDynamicRetrievalScore?: number;
}

/**
 * Result from calling generateContentStream.
 * It constains both the stream and the final aggregated response.
 * @public
 */
export interface GenerateContentStreamResult {
  stream: AsyncGenerator<EnhancedGenerateContentResponse>;
  response: Promise<EnhancedGenerateContentResponse>;
}

/**
 * Params for calling embedContent
 * @public
 */
export interface EmbedContentRequest {
  content: Content;
  taskType?: TaskType;
  title?: string;
}

/**
 * Task type for embedding content.
 * @public
 */
export enum TaskType {
  TASK_TYPE_UNSPECIFIED = 'TASK_TYPE_UNSPECIFIED',
  RETRIEVAL_QUERY = 'RETRIEVAL_QUERY',
  RETRIEVAL_DOCUMENT = 'RETRIEVAL_DOCUMENT',
  SEMANTIC_SIMILARITY = 'SEMANTIC_SIMILARITY',
  CLASSIFICATION = 'CLASSIFICATION',
  CLUSTERING = 'CLUSTERING',
}

/**
 * Gemini model object
 * @public
 */
export interface Model {
  name: string;
  baseModelId: string;
  version: string;
  displayName: string;
  description: string;
  inputTokenLimit: number;
  outputTokenLimit: number;
  supportedGenerationMethods: string[];
  temperature: number;
  maxTemperature: number;
  topP: number;
  topK: number;
}

/**
 * Response from calling listModels
 * @public
 */
export interface ListModelsResponse {
  models: Model[];
  nextPageToken?: string;
}

/**
 * Response from calling embedContent
 * @public
 */
export interface EmbedContentResponse {
  embedding: ContentEmbedding;
}

/**
 * A single content embedding.
 * @public
 */
export interface ContentEmbedding {
  values: number[];
}
