import subprocess, os

output = subprocess.check_output(["git", "diff", "--name-only", "--diff-filter=U"]).decode("utf-8")
for line in output.splitlines():
    file = line.strip()
    print(f"\n--- {file} ---")
    with open(file, "r") as f:
        content = f.read()
    import re
    blocks = re.findall(r'(<<<<<<< HEAD.*?>>>>>>> origin/main)', content, flags=re.DOTALL)
    for b in blocks:
        print(b)
        print("==========")
