with open("py/packages/genkit/src/genkit/_core/_plugin.py", "r") as f:
    content = f.read()

import re
# First block
content = re.sub(
    r'<<<<<<< HEAD\n=======\n(.*?)\n>>>>>>> origin/main',
    r'\1',
    content,
    flags=re.DOTALL | re.MULTILINE
)

with open("py/packages/genkit/src/genkit/_core/_plugin.py", "w") as f:
    f.write(content)
