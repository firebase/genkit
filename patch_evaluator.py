with open("py/packages/genkit/src/genkit/_ai/_evaluator.py", "r") as f:
    content = f.read()

import re
content = re.sub(r'<<<<<<< HEAD\n.*?=======\n>>>>>>> origin/main\n', '', content, flags=re.DOTALL)

with open("py/packages/genkit/src/genkit/_ai/_evaluator.py", "w") as f:
    f.write(content)
