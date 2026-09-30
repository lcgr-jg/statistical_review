from pathlib import Path
import re
t = Path("rate_anatomy_replication/docs/OVERVIEW.md").read_text(encoding="utf-8")
# Exclude title line and deep-doc footer for body word count
lines = t.splitlines()
body_lines = []
for line in lines:
    if line.startswith("# "):
        continue
    if line.startswith("**Deeper"):
        break
    body_lines.append(line)
body = "\n".join(body_lines)
words = re.findall(r"[A-Za-z0-9']+", body)
print("body_word_count", len(words))
print("total_word_count", len(re.findall(r"[A-Za-z0-9']+", t)))
