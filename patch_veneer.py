import re
with open("py/packages/genkit/tests/genkit/veneer/veneer_test.py", "r") as f:
    content = f.read()

# Replace the conflict block with the HEAD content, but rename EvalFnResponse to EvaluatorResponse
head_match = re.search(r'<<<<<<< HEAD\n(.*?)\n=======\n.*?\n>>>>>>> origin/main', content, flags=re.DOTALL)
if head_match:
    head_content = head_match.group(1).replace('EvalFnResponse', 'EvaluatorResponse')
    content = content[:head_match.start()] + head_content + content[head_match.end():]

with open("py/packages/genkit/tests/genkit/veneer/veneer_test.py", "w") as f:
    f.write(content)
