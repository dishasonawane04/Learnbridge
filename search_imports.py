import os
import re

search_path = 'd:\\DISHA\\learnbridge'
pattern = re.compile(r'(from langchain.*import.*HuggingFaceEmbeddings|import sentence_transformers)', re.IGNORECASE)

print(f"Searching for legacy imports in {search_path}...")

matches = []
for root, dirs, files in os.walk(search_path):
    if '__pycache__' in root:
        continue
    for file in files:
        if file.endswith('.py'):
            path = os.path.join(root, file)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for i, line in enumerate(content.splitlines()):
                        if pattern.search(line):
                            matches.append(f"{path}:{i+1}: {line.strip()}")
            except Exception:
                pass

for m in matches:
    print(m)

if not matches:
    print("No legacy imports found.")
