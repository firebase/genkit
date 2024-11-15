import { ModelMiddleware } from "@genkit-ai/ai/model"
import { ChecksEvaluationMetric } from "./evaluation"

export function checksMiddleware(options?: {
  metrics?: ChecksEvaluationMetric[]
}): ModelMiddleware {
  return async (req, next) => {
    console.log("Checks middleware request: ", req)
    return next(req)
  }
} 