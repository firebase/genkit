module.exports = {
  evaluators: [
    {
      flowName: 'generateDraftFlow',
      extractors: {
        context: (trace) => {
          const rootSpan = Object.values(trace.spans).find(
            (s) =>
              s.attributes['genkit:type'] === 'flow' &&
              s.attributes['genkit:name'] === 'generateDraftFlow'
          );
          if (!rootSpan) return JSON.stringify([]);

          const input = JSON.parse(rootSpan.attributes['genkit:input']);
          return JSON.stringify([JSON.stringify(input)]);
        },
        // Keep the default extractors for input and output
      },
    },
    {
      flowName: 'classifyInquiryFlow',
      extractors: {
        context: (trace) => {
          const rootSpan = Object.values(trace.spans).find(
            (s) =>
              s.attributes['genkit:type'] === 'flow' &&
              s.attributes['genkit:name'] === 'classifyInquiryFlow'
          );
          if (!rootSpan) return JSON.stringify([]);

          const input = JSON.parse(rootSpan.attributes['genkit:input']);
          return JSON.stringify([JSON.stringify(input)]);
        },
        // Keep the default extractors for input and output
      },
    },
  ],
};
