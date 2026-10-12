with open("py/packages/genkit/src/genkit/_core/_plugin.py", "r") as f:
    lines = f.readlines()

out = []
skip = False
for line in lines:
    if line.startswith("<<<<<<<"):
        continue
    if line.startswith("======="):
        continue
    if line.startswith(">>>>>>>"):
        continue
    out.append(line)

with open("py/packages/genkit/src/genkit/_core/_plugin.py", "w") as f:
    f.writelines(out)
