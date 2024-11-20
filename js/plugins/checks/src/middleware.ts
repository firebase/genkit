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
    console.log("Checks middleware request: ", req)

    for (const message of req.messages) {
      for (const content of message.content) {
        if (content.text) {
          const response = await guardrails.classifyContent(
            content.text,
            options.metrics)

          const violatedPolicies = response.policyResults.filter(
            policy => policy.violationResult === "VIOLATIVE"
          )

          if (violatedPolicies.length > 0) {
            const violationString = violatedPolicies.map(policy => `${policy.policyType}: ${policy.violationResult}(${policy.score})`).join(", ")
            throw new Error(`Input message violated Checks policy ${violationString}`)
          }

          console.log("Violated Policies: ", violatedPolicies)
        }
      }
    }



    return next(req)
  }
} 