import os

path = r'D:\DISHA\learnbridge\templates\base.html'
print(f"Reading {path}...")
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Look for the specific split tag across lines
pattern = r'{% if active_course %}{{ active_course.title\|truncatechars:15 }}{% else %}Select Course{% endif\s*\n\s*%}'
replacement = r'{% if active_course %}{{ active_course.title|truncatechars:15 }}{% else %}Select Course{% endif %}'

import re
new_content = re.sub(pattern, replacement, content)

if new_content == content:
    print("No change needed or pattern not found.")
else:
    print("Pattern found! Writing changes...")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Done.")
