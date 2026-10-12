import re

files = [
    "py/packages/genkit-evaluators/src/genkit_evaluators/_plugin.py",
    "py/packages/genkit-google-genai/src/genkit_google_genai/_evaluators/_evaluation.py",
    "py/samples/evaluators/src/main.py",
]

for file in files:
    with open(file, "r") as f:
        content = f.read()
    
    # Replace block with HEAD's dict[str, Any] but using main's EvaluatorResponse
    def replacer(m):
        head = m.group(1)
        # return head but replace EvalFnResponse with EvaluatorResponse
        return head.replace("EvalFnResponse", "EvaluatorResponse")
    
    new_content = re.sub(r'<<<<<<< HEAD\n(.*?)\n=======\n.*?\n>>>>>>> origin/main', replacer, content, flags=re.DOTALL)
    with open(file, "w") as f:
        f.write(new_content)

# vertex_ai_evaluators_test.py
with open("py/packages/genkit-google-genai/tests/vertex_ai_evaluators_test.py", "r") as f:
    content = f.read()
content = re.sub(r'<<<<<<< HEAD\n.*?\n=======\n(.*?)\n>>>>>>> origin/main', r'\1', content, flags=re.DOTALL)
with open("py/packages/genkit-google-genai/tests/vertex_ai_evaluators_test.py", "w") as f:
    f.write(content)

# imports
for file in [
    "py/packages/genkit/src/genkit/_ai/_aio.py",
    "py/packages/genkit/src/genkit/_ai/_evaluator.py",
    "py/packages/genkit/src/genkit/evaluator/__init__.py",
    "py/packages/genkit/tests/genkit/core/endpoints/reflection_test.py",
    "py/packages/genkit/tests/genkit/veneer/veneer_test.py"
]:
    with open(file, "r") as f:
        content = f.read()
    # for imports, main is usually right since they renamed it to EvaluatorResponse
    content = re.sub(r'<<<<<<< HEAD\n.*?\n=======\n(.*?)\n>>>>>>> origin/main', r'\1', content, flags=re.DOTALL)
    with open(file, "w") as f:
        f.write(content)

