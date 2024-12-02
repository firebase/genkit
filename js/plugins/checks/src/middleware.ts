import { ModelMiddleware } from "@genkit-ai/ai/model"
import { ChecksEvaluationMetric } from "./metrics"
import { GoogleAuth } from "google-auth-library"
import { Guardrails } from "./guardrails"

export function checksMiddleware(options: {
  auth: GoogleAuth,
  metrics: ChecksEvaluationMetric[]
  projectId?: string,
}): ModelMiddleware {

  const guardrails = new Guardrails(options.auth, options?.projectId)

  return async (req, next) => {
    for (const message of req.messages) {
      for (const content of message.content) {
        if (content.text) {
          const response = await guardrails.classifyContent(content.text, options.metrics)

          console.log(`Request message: ${content.text}: `, response.policyResults)

          // Filter for violations
          const violatedPolicies = response.policyResults.filter(
            policy => policy.violationResult === "VIOLATIVE"
          )

          // If any input message violates a checks policy. Stop processing, 
          // return a blocked response and list of violated policies.
          if (violatedPolicies.length > 0) {
            return {
              finishReason: "blocked",
              finishMessage: `Model input violated Checks policies: [${violatedPolicies.map((result) => result.policyType).join(" ")}], further processing blocked.`,
            }
          }
        }
      }
    }

    const generatedContent = await next(req)

    for (const candidate of generatedContent.candidates ?? []) {
      for (const content of candidate.message.content ?? []) {

        if (content.text) {
          const response = await guardrails.classifyContent(content.text, options.metrics)

          console.log(`Response message: ${content.text}: `, response.policyResults)

          // Filter for violations
          const violatedPolicies = response.policyResults.filter(
            policy => policy.violationResult === "VIOLATIVE"
          )

          // If the output message violates a checks policy. Stop processing, 
          // return a blocked response and list of violated policies.
          if (violatedPolicies.length > 0) {
            return {
              finishReason: "blocked",
              finishMessage: `Model output violated Checks policies: [${violatedPolicies.map((result) => result.policyType).join(" ")}], output blocked.`,
            }
          }
        }
      }
    }

    return generatedContent
  }
} 